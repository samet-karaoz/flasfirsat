import re

PHONETIC_MAP = {
    r"\bde['’]?longhi\b": "Delongi",
    r"\bxiaomi\b": "Şaomi",
    r"\bugreen\b": "Yugrin",
    r"\banker\b": "Enkır",
    r"\bsoundcore\b": "Saundkor",
    r"\bphilips\b": "Filips",
    r"\bdyson\b": "Daysın",
    r"\bbraun\b": "Bıraun",
    r"\boral[\s\-]?b\b": "Oral Bi",
    r"\blogitech\b": "Locitek",
    r"\bhuawei\b": "Hüveey",
    r"\bbaseus\b": "Beysus",
    r"\bhyperx\b": "Haypır Eks",
    r"\brazer\b": "Reyzır",
    r"\bsteelseries\b": "Stilseris",
    r"\bstanley\b": "Stenli",
    r"\bnespresso\b": "Nespreso",
    r"\broborock\b": "Roborok",
    r"\bapple\b": "Epıl",
    r"\bairpods\b": "Eırpods",
    r"\bairfryer\b": "Eyrfırayır",
    r"\bairwrap\b": "Eyrvep",
    r"\bbluetooth\b": "Blutut",
    r"\bwireless\b": "Vayırlıs",
    r"\bpowerbank\b": "Pavırbenk"
}

def to_phonetic_turkish(text: str) -> str:
    """
    Metin içindeki yabancı marka ve teknik terimleri,
    yapay zeka TTS ses motorunun kusursuz ve doğal telaffuz etmesi için
    Türkçe fonetik karşılıklarıyla değiştirir.
    """
    if not text:
        return ""
    res = text
    for pattern, phonetic in PHONETIC_MAP.items():
        res = re.sub(pattern, phonetic, res, flags=re.IGNORECASE)
    return res
