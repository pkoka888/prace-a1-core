"""Fictional, programmatically rendered document evidence."""
from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont
from src.document_core.ocr_result import OcrRegion, OcrResult
from src.document_core.serialization import content_hash
from src.document_core.interpretation import check_digit

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
OP = ["CESKA REPUBLIKA", "OBCANSKY PRUKAZ", "PRIJMENI: TESTOVA", "JMENO: ALFA",
      "DATUM NAROZENI: 15.03.1990", "CISLO DOKLADU: TST000001", "PLATNOST DO: 31.12.2099"]
ZP = ["CZ EHIC", "3. PRIJMENI: TESTOVA", "4. JMENO: ALFA", "5. DATUM NAROZENI: 15.03.1990",
      "6. CISLO POJISTENCE: INS000001", "7. KOD POJISTOVNY: 111", "8. CISLO KARTY: CARD000001", "9. PLATNOST DO: 31.12.2099"]
PASSPORT = ["CESKA REPUBLIKA", "CESTOVNI PAS", "PRIJMENI: TESTOVA", "JMENO: ALFA",
            "DATUM NAROZENI: 15.03.1990", "CISLO PASU: PTS000001", "PLATNOST DO: 31.12.2099"]


def card(lines, border=False):
    image = Image.new("RGB", (720, 420), "white")
    draw = ImageDraw.Draw(image)
    if border:
        draw.rectangle((3, 3, 716, 416), outline="black", width=3)
    font = ImageFont.truetype(FONT, 25)
    for i, text in enumerate(lines):
        draw.text((24, 20+i*42), text, font=font, fill="black")
    return image


def png(image):
    stream = BytesIO(); image.save(stream, format="PNG"); return stream.getvalue()


def fake_result(lines, content=b"synthetic"):
    return OcrResult(tuple(OcrRegion(str(uuid4()), 0, ((20,20+i*40),(680,20+i*40),(680,45+i*40),(20,45+i*40)),
                                    line, .99, True) for i, line in enumerate(lines)), 1, "synthetic", "test", content_hash(content))


class ScriptedEngine:
    def __init__(self, reads):
        self.reads = iter(reads)
    def process(self, content):
        return fake_result(next(self.reads), content)


def td1(number="TST000001", surname="TESTOVA", birth="900315", expiry="991231"):
    a = "I<CZE"+number+check_digit(number)+"<"*15
    middle = birth+check_digit(birth)+"F"+expiry+check_digit(expiry)+"CZE"+"<"*11
    b = middle+check_digit(a[5:30]+middle[:7]+middle[8:15]+middle[18:29])
    c = (surname+"<<ALFA").ljust(30,"<")
    return [a,b,c]


def td3():
    a = ("P<CZE"+"TESTOVA<<ALFA").ljust(44,"<")
    number,birth,expiry="PTS000001","900315","991231"
    b=number+check_digit(number)+"CZE"+birth+check_digit(birth)+"F"+expiry+check_digit(expiry)+"<"*14+"0"
    b+=check_digit(b[:10]+b[13:20]+b[21:43])
    return [a,b]
