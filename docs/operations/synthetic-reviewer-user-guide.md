# Uživatelské pokyny — syntetické prostředí Release 1A

Tento návod je určený jen pro testovací prostředí. Používejte pouze
syntetické údaje; nevkládejte skutečné údaje pracovníků, dokumenty ani
finanční záznamy.

## Přihlášení

Otevřete v prohlížeči:

```text
http://127.0.0.1:8000/accounts/login/
```

Pokud se stránka zobrazí bez stylů, použijte tvrdé obnovení stránky
(`Ctrl+Shift+R`). Aplikace nyní načítá CSS lokálně; pro přihlášení není
potřeba přístup k externímu CDN.

Přístup je pouze na pozvánku. Pro místní syntetický účet `admin` může
operátor vytvořit nové dočasné přihlášení tímto příkazem:

```bash
export SYNTHETIC_REVIEW_SECRET="$(cat secrets/synthetic_review.key)"
export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review

venv/bin/python scripts/reset_synthetic_reviewer_password.py \
  --login admin \
  --confirm \
  --show-totp-code
```

Příkaz vypíše uživatelské jméno, nově vytvořené dočasné heslo a aktuální
šestimístný TOTP kód. Heslo se tím změní a předchozí přestane fungovat.
TOTP kód je krátkodobý; zadejte jej hned po vytištění. Tyto údaje se
nevkládají do tiketů, dokumentace ani Git repozitáře.

## Kontrola Release 1A

Po přihlášení aplikace otevře `/review/`. Kontrola má čtyři sekce:

1. Pracovník
2. Dokument a kontrola OCR
3. Přiřazení
4. Příprava a kontrola A1

U každé sekce otevřete **Zobrazit**, projděte syntetický scénář a zvolte
stav:

- **Rozpracováno** — kontrola ještě není dokončena.
- **Dokončeno** — sekce odpovídá očekávanému chování.
- **Vyžaduje opravu** — nalezený problém; přidejte stručnou poznámku bez
  osobních údajů.

Tlačítko **Pokračovat ke kontrole** otevře souhrn. Schválení Release 1A je
možné pouze tehdy, když jsou všechny čtyři sekce dokončené a automatická
kontrola připravenosti projde. Schválení vytváří neměnnou účtenku; před
schválením proto ověřte stav pečlivě.

## Odhlášení

V mobilním zobrazení použijte v horní liště **Účet**, potom potvrďte
**Odhlásit se**. Na počítači se odhlaste z účtu v horní liště. Po odhlášení
nesmí být `/review/` dostupné bez nového přihlášení a TOTP.

## Týdenní rozpočet — současný prototyp

Položka **Rozpočet · náhled** je pouze návrh uživatelského rozhraní pro Janovo
posouzení. Ukazuje syntetické ukázkové údaje a pivot podle pracovníka a
kategorie.

V této fázi:

- žádný záznam se neukládá;
- tlačítko CSV nevytváří skutečný export;
- předchozí/další týden nemění data;
- smazání položky a poznámky nejsou trvalé;
- obsah nelze používat jako finanční podklad ani jej sdílet jako skutečný
  rozpočet.

Prototyp je vhodný k ověření rozložení, názvů kategorií, mobilního ovládání
a formátu souhrnu pro WhatsApp. Skutečné finanční záznamy budou vyžadovat
samostatně schválenou datovou, bezpečnostní a účetní implementaci.

## Jak nahlásit problém

Zapište URL, kroky k opakování, očekávaný a skutečný výsledek a snímek
obrazovky pouze se syntetickými údaji. Nikdy nepřikládejte skutečný dokument,
rodné číslo, adresu, mzdu nebo přihlašovací údaje.
