import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID
import pytest
from PIL import Image
from src.document_core.images import decode_pages, Segmenter
from src.document_core.interpretation import Classifier, FieldInterpreter, parse_mrz
from src.document_core.pipeline import DocumentProcessor
from src.document_core.ocr_result import UnlocatedTextError, UnalignedOutputError, ContractError
from src.document_core.adapters.rapidocr import _convert_rapidocr_output, _engine_version
from src.document_core.cli import process_files
from src.document_core.serialization import result_hash, atomic_bytes
from .helpers import OP, ZP, PASSPORT, card, png, fake_result, ScriptedEngine, td1, td3


def pipeline(reads):
    return DocumentProcessor(lambda: ScriptedEngine(reads))


def fields(document):
    return {f["field"]: f["value"] for f in document["fields"]}


def test_engine_alignment_ids_metadata_and_empty_time():
    r = SimpleNamespace(boxes=[[[0,0],[20,0],[20,10],[0,10]]], txts=("test",), scores=(.9,), elapse=.2)
    a = _convert_rapidocr_output(r,b"a",_engine_version())
    b = _convert_rapidocr_output(r,b"b",_engine_version())
    assert UUID(a.regions[0].region_id).version == 4
    assert a.regions[0].region_id != b.regions[0].region_id
    assert a.engine_version != "unknown"
    assert not hasattr(a,"raw_output")
    r.boxes=[]
    with pytest.raises(UnlocatedTextError): _convert_rapidocr_output(r,b"a","test")
    r.txts=();r.scores=()
    assert _convert_rapidocr_output(r,b"a","test").elapse_ms==200
    r.boxes=[[[0,0],[20,0],[20,10],[0,10]]]
    with pytest.raises(UnalignedOutputError): _convert_rapidocr_output(r,b"a","test")


@pytest.mark.parametrize("lines,kind",[(OP,"op"),(ZP,"zp"),(PASSPORT,"passport")])
def test_typed_fields_and_readiness(lines,kind):
    doc=pipeline([lines,lines]).process(png(card(lines)))["documents"][0]
    assert doc["classification"]["type"]==kind
    assert fields(doc)["birth_date"]=="1990-03-15"
    assert fields(doc)["expiry_date"]=="2099-12-31"
    assert doc["completeness"]["field_sufficiency"]["sufficient"]
    assert not doc["completeness"]["workflow_ready"]
    assert doc["association"]["status"]=="unassigned"
    assert all(f["evidence"] for f in doc["fields"])
    if kind=="op":
        assert doc["classification"]["side"]=="front"
        assert doc["completeness"]["missing_sides"]==["back"]


def test_unknown_and_invalid_dates_are_not_invented():
    content=png(card(OP))
    doc=pipeline([["POSSIBLY A CARD"],["POSSIBLY A CARD"]]).process(content)["documents"][0]
    assert doc["classification"]["type"] is None
    assert doc["fields"]==[]
    invalid=[line.replace("15.03.1990","29.02.2002") for line in OP]
    doc=pipeline([invalid,invalid]).process(content)["documents"][0]
    assert "invalid_date" in next(f["findings"] for f in doc["fields"] if f["field"]=="birth_date")
    assert not doc["completeness"]["field_sufficiency"]["sufficient"]


def test_enhancement_disagreement_keeps_both_reads():
    changed=[line.replace("TESTOVA","DRUHA") for line in OP]
    doc=pipeline([OP,changed]).process(png(card(OP)))["documents"][0]
    assert "enhancement_disagreement" in doc["findings"]
    assert next(d for d in doc["field_diff"] if d["field"]=="family_name")["disagreement"]
    assert fields(doc)["family_name"]=="TESTOVA"
    assert next(f["value"] for f in doc["enhanced_fields"] if f["field"]=="family_name")=="DRUHA"
    assert doc["association"]["worker_id"] is None


def test_mrz_td1_td3_checksum_and_century():
    for lines,fmt in ((td1(),"td1"),(td3(),"td3")):
        result=fake_result(lines)
        mrz=parse_mrz(result.regions)
        assert mrz["valid"] and mrz["format"]==fmt
        classification=Classifier().classify(result.regions)
        props,findings=FieldInterpreter().interpret(result.regions,classification)
        assert "birth_date_century_unresolved" in findings
        assert "birth_date" not in {p["field"] for p in props}
        broken=lines.copy(); broken[1]="1"+broken[1][1:]
        assert not parse_mrz(fake_result(broken).regions)["valid"]


def test_side_matching_typed_id_conflict_and_duplicates():
    front=pipeline([OP,OP]).process(png(card(OP)))["documents"][0]
    back=pipeline([td1(),td1()]).process(png(card(td1())))["documents"][0]
    result=DocumentProcessor().combine([front,back])
    assert result["documents"][0]["paired_with"]==back["document_id"]
    assert back["paired_with"]==front["document_id"]
    wrong=pipeline([td1(surname="DRUHA"),td1(surname="DRUHA")]).process(png(card(td1(surname="DRUHA"))))["documents"][0]
    DocumentProcessor().combine([front,wrong])
    assert front["paired_with"] is None
    assert "identity_evidence_conflict" in front["matching_findings"]
    duplicate=pipeline([OP,OP]).process(png(card(OP)))["documents"][0]
    DocumentProcessor().combine([front,duplicate])
    assert duplicate["duplicate_of"]==front["document_id"]


def test_worker_association_requires_exact_typed_identifier():
    doc=pipeline([OP,OP]).process(png(card(OP)))["documents"][0]
    workers=[{"worker_id":"one","family_name":"TESTOVA","identifiers":[]}]
    DocumentProcessor().combine([doc],workers)
    assert doc["association"]["status"]=="unassigned"
    workers[0]["identifiers"]=[{"type":"op_document_number","issuer":"cz","value":"TST000001"}]
    DocumentProcessor().combine([doc],workers)
    assert doc["association"]["status"]=="proposed"
    assert not doc["association"]["accepted"]
    workers[0]["identity_fields"] = {"family_name": "DRUHA"}
    DocumentProcessor().combine([doc], workers)
    assert doc["association"]["worker_id"] is None
    assert doc["association"]["findings"] == ["worker_identity_conflict"]
    workers[0].pop("identity_fields")
    workers.append({**workers[0],"worker_id":"two"})
    DocumentProcessor().combine([doc],workers)
    assert doc["association"]["status"]=="ambiguous"


def test_mixed_image_segmentation_before_field_processing():
    canvas=Image.new("RGB",(1500,470),"white")
    canvas.paste(card(OP,True),(10,15));canvas.paste(card(ZP,True),(760,15))
    pages=decode_pages(png(canvas))
    assert len(Segmenter().segment(pages[0]))==2
    docs=pipeline([OP,OP,ZP,ZP]).process(png(canvas))["documents"]
    assert [d["classification"]["type"] for d in docs]==["op","zp"]
    assert min(p[0] for p in docs[1]["ocr"]["regions"][0]["polygon"])>700


def test_pdf_pages_and_encrypted_rejected():
    import fitz
    pdf=fitz.open()
    for _ in range(2): pdf.new_page(width=400,height=250)
    content=pdf.tobytes()
    assert len(decode_pages(content))==2
    encrypted=pdf.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw="synthetic",user_pw="synthetic")
    with pytest.raises(ContractError,match="PDF_ENCRYPTED"): decode_pages(encrypted)
    with pytest.raises(ContractError): decode_pages(b'%PDF-fake')


def test_label_value_boxes_and_identifier_types():
    lines=["CESKA REPUBLIKA","OBCANSKY PRUKAZ","PRIJMENI:","TESTOVA","RODNE CISLO: 900315/1234","CAN: 123456"]
    result=fake_result(lines)
    props,_=FieldInterpreter().interpret(result.regions,Classifier().classify(result.regions))
    result={f["field"]:f["value"] for f in props}
    assert result["family_name"]=="TESTOVA"
    assert result["personal_identifier"]=="900315/1234"
    assert "document_number" not in result and "residence_house_number" not in result


def test_failure_receipt_and_partial_batch_without_paths(tmp_path,capsys):
    missing=tmp_path/"private-synthetic-name.png"
    out=tmp_path/"out"
    assert process_files([missing],out)==1
    receipt=json.loads(next(out.glob('*/result.json')).read_text())
    assert receipt["status"]=="failed" and receipt["error_tag"]=="INPUT_NOT_FOUND"
    assert receipt["output_hash"]==""
    assert str(missing) not in capsys.readouterr().err
    image=tmp_path/"misleading-passport-name.png";image.write_bytes(png(card(OP)))
    assert process_files([image,missing],tmp_path/"batch",processor=pipeline([OP,OP]))==1
    receipt=json.loads(next((tmp_path/"batch").glob('*/result.json')).read_text())
    assert receipt["status"]=="partial"
    assert receipt["documents"][0]["classification"]["type"]=="op"
    assert receipt["output_hash"]==result_hash(receipt["ocr"])
    assert next((tmp_path/"batch").glob('*/*.source')).read_bytes()==image.read_bytes()


def test_atomic_replace_failure_preserves_old_file(tmp_path,monkeypatch):
    target=tmp_path/"result.json";target.write_bytes(b"previous")
    def fail(*args): raise PermissionError("synthetic")
    monkeypatch.setattr("src.document_core.serialization.os.replace",fail)
    with pytest.raises(PermissionError): atomic_bytes(target,b"new")
    assert target.read_bytes()==b"previous"
    assert list(tmp_path.iterdir())==[target]


def test_bounded_batch_isolates_invalid_input():
    class Engine:
        def process(self, content): return fake_result(OP, content)
    proc=DocumentProcessor(Engine)
    result=proc.process_batch([png(card(OP)),b"bad"],max_concurrency=2)
    assert [r["status"] for r in result["runs"]]==["completed","failed"]
    with pytest.raises(ValueError): proc.process_batch([],max_concurrency=5)


@pytest.mark.parametrize("lines,kind",[(OP,"op"),(ZP,"zp"),(PASSPORT,"passport")])
def test_real_ocr_document_semantics_offline(lines,kind):
    result=DocumentProcessor().process(png(card(lines)))
    doc=result["documents"][0]
    assert doc["classification"]["type"]==kind
    assert fields(doc)["family_name"]=="TESTOVA"
    assert fields(doc)["birth_date"]=="1990-03-15"
    assert fields(doc)["expiry_date"]=="2099-12-31"


def test_bilingual_labels_do_not_become_values():
    result=fake_result(["CESKA REPUBLIKA","OBCANSKY PRUKAZ","PRIJMENI / SURNAME","TESTOVA"])
    props,_=FieldInterpreter().interpret(result.regions,Classifier().classify(result.regions))
    assert [(f["field"],f["value"]) for f in props]==[("family_name","TESTOVA")]
