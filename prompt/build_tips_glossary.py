#!/usr/bin/env python
"""Build the normative Tips glossary (JA / EN / FR) from the game's own data.

The <tips,N,label> tags scattered through the script ARE the game's glossary of
specialised terms. We mine them from the extracted corpus rather than guessing,
then attach a fixed French rendering to each id.

Output: prompt/tips_glossary.tsv  (id, ja, en, fr)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "..", "extracted", "all.jsonl")
OUT = os.path.join(HERE, "tips_glossary.tsv")

TAG = re.compile(r"<tips,(\d+),([^>]*)>")
RUBY = re.compile(r"\[[^\]]*\]")

# Fixed French renderings, keyed by the game's own tips id.
FR = {
    1: "l’Organisation", 2: "machine à voyager dans le temps", 3: "nom véritable",
    4: "Radio Kaikan", 5: "onde électromagnétique", 6: "capsule-jouet",
    7: "RaiNet Kakeru", 8: "John Titor", 10: "téléviseur à tube cathodique",
    11: "cosplay", 12: "super hackeur", 13: "lojik", 14: "un certain manga de tennis",
    15: "@channel", 16: "me regarde pas", 17: "filles en 2D", 18: "waifu",
    20: "chuunibyou", 21: "Alpaga-man", 22: "jeu interactif", 23: "rencontre IRL", 27: "UPX",
    28: "Doc P", 29: "four à micro-ondes", 30: "sérendipité",
    31: "canon à particules Bit", 32: "Bambou-Hélicam",
    33: "Serait-ce un Ora Ora ?!", 34: "Moad Snake",
    35: "« J’ai encore relié un objet sans intérêt » — par Goemon",
    36: "sabre Cyalume", 37: "Ghost in the Ball", 38: "règle de Hund", 39: "ATF",
    40: "Daibiru", 41: "Louise-chan", 42: "ÇA ARRIVE", 43: "université Tokyo Denki",
    44: "Einstein", 45: "théorie de la relativité", 46: "particule élémentaire",
    47: "théorie des supercordes", 48: "1,21 gigowatt", 49: "Los Angeles",
    50: "effet Urashima", 51: "principe de causalité", 52: "paradoxe temporel",
    53: "loi de conservation de la masse", 54: "livre farfelu",
    55: "principe d’autocohérence", 56: "pont Manseibashi",
    57: "sanctuaire Kanda Myojin", 58: "rue piétonne", 59: "photographes amateurs",
    60: "école Seishin Zanma", 61: "fujoshi", 62: "ComiMa", 63: "Kirari-chan",
    64: "Une fille aussi mignonne ne peut pas être une fille", 65: "ōnusa",
    68: "IBN", 69: "les anons", 70: "maladie de Creutzfeldt-Jakob", 71: "troll",
    72: "SERN", 73: "+ dtails", 74: "dystopie", 75: "twa", 76: "vzot",
    77: "sérieux", 78: "mdr", 79: "up", 80: "maid café", 81: "festival",
    82: "légende urbaine", 83: "PC-98", 84: "MI6", 85: "curée médiatique",
    86: "société éditoriale", 87: "attaque en combo", 88: "otaku",
    89: "Marbre de Réalité", 90: "trokiant", 91: "source", 92: "tro cher",
    93: "Wiki", 94: "FrePara", 95: "dzl", 96: "CRT", 97: "apparition",
    98: "paradoxe des jumeaux", 99: "Tipler", 100: "Chevrolé", 101: "ton blog",
    102: "diagramme de Penrose", 103: "en français stp", 104: "cépabo",
    105: "singularité", 106: "TA GUEULEEEE", 107: "horloge à césium",
    108: "pseudo fixe", 109: "X68000", 110: "yeux vairons",
    111: "transition de phase", 112: "structure fractale", 113: "éponge de Menger",
    114: "Edison", 115: "téléportation", 116: "réplique explicative",
    117: "zombie", 118: "arts martiaux", 119: "noradrénaline",
    120: "téléportation quantique", 121: "la personne derrière", 122: "DOS",
    124: "Sanpo", 125: "recomand", 126: "HTML", 127: "HTTP",
    128: "World Wide Web", 129: "URL", 130: "airsoft", 131: "APL",
    132: "BASIC", 133: "stp", 134: "art ASCII", 135: "réponse sérieuse",
    136: "mondes parallèles", 137: "séisme de Shibuya", 138: "mouvement étudiant",
    139: "nationaliste du Net", 140: "bug de l’an 2000", 141: "oden en conserve",
    142: "SQL", 143: "professeur Excite", 144: "synchronicité", 145: "cracking",
    146: "autonome", 148: "Ragnarök", 149: "théorie du complot",
    150: "La Machine à explorer le temps de H. G. Wells", 151: "nerf périphérique",
    152: "mode terminal", 153: "Gargari-kun", 154: "motel", 155: "double sens",
    156: "jpg", 157: "Comité des 300", 158: "googler", 159: "collisionneur",
    160: "coffre de Laegjarn", 161: "MiouTube", 162: "la vidéo en question",
    163: "moéfication", 164: "séquence de transformation",
    165: "horizon des événements", 166: "singularité nue", 168: "NASA",
    169: "Opération Urd", 170: "réponse finale", 171: "pénicilline",
    172: "rayons X", 173: "dynamite", 175: "tsundere", 176: "théorie du chaos",
    177: "lobotomie", 178: "Loto 6", 179: "lobe frontal", 181: "lavage de cerveau",
    182: "hippocampe", 183: "ramen en conserve", 184: "maître Anzai",
    185: "meufs mainstream (lol)", 186: "téléphone décoré", 187: "Mistilteinn",
    188: "yuri", 189: "low angler", 190: "japanimation",
    191: "annales akashiques", 192: "éditions Minmei", 193: "capsule temporelle",
    194: "bipeur", 195: "niveau magicien", 196: "4e dimension",
    197: "loi de Janet", 198: "flag", 199: "trou blanc", 200: "exaoctet",
    201: "dessinateur", 202: "Gunbam", 203: "Blood Tune", 204: "cosplayeuse",
    205: "détective privé", 206: "Eldhrímnir", 207: "spam", 208: "forum",
    209: "+1", 210: "flag de mort", 211: "accès root",
    212: "Assemblée nationale française", 213: "ms", 214: "magnétron",
    215: "neurosciences", 216: "Mindorz", 217: "chaude", 218: "Opération Verthandi",
    219: "influx nerveux", 220: "lobe temporal", 221: "gyrus parahippocampique",
    222: "neurones", 223: "Institut de recherche en psychophysiologie", 224: "OS",
    225: "VIP", 226: "ancre", 227: "Nullpo", 228: "ptdr", 229: "champ électrique",
    230: "CA3", 231: "décodage", 232: "couper-coller", 233: "copier-coller",
    234: "interprétation de Copenhague", 235: "fonction d’onde",
    236: "signal de récupération mnésique descendant", 237: "Heidegger",
    238: "Ayamein", 239: "AK-47", 240: "déjà-vu", 241: "Bukuro",
    242: "sanctuaire Kishimojin", 243: "Starbecks", 244: "racaille",
    245: "arété", 246: "conjecture de protection de la chronologie",
    247: "la Résistance", 248: "déterminisme", 249: "Échelon",
    252: "accro à Nico", 253: "magicien", 254: "effet placebo", 255: "svp",
    257: "Big Sight", 258: "ruban de Möbius", 259: "OOPArt", 260: "ça sert à qui ?",
    261: "hahaha", 262: "Stand", 263: "Cheshire Break",
    264: "explosion de poussières", 265: "normie", 266: "bien vu celle-là",
    267: "Rose-Croix", 268: "alchimie", 269: "résumé en 3 lignes",
    270: "Isaac Newton", 271: "Miko Miko Overdrive", 272: "seks",
    273: "BladeWorks", 274: "bouffe dégueu", 275: "acétylcholine",
    277: "un truc genre pied-de-biche", 279: "light novel", 280: "Europol",
    281: "grenade assourdissante", 282: "perruque", 283: "kebab",
    284: "flocons d’avoine", 285: "kit de couture", 286: "sniff sniff",
    287: "ACTH", 288: "répétition élaborative", 289: "triche",
    290: "Opération Skuld",
}

# Pairs where the official English localisation swapped the two labels.
# Recorded so nobody "fixes" our French back to match the English.
EN_SWAPPED = {58, 59, 185, 186, 219, 220, 225, 226, 267, 268}


def main():
    if not os.path.exists(CORPUS):
        sys.exit(f"missing {CORPUS} - run extract_dialogue.py --all first")

    seen = {}
    with open(CORPUS, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            ja, en = r["texts"].get("ja", ""), r["texts"].get("en", "")
            mj = {int(m.group(1)): m.group(2) for m in TAG.finditer(ja)}
            me = {int(m.group(1)): m.group(2) for m in TAG.finditer(en)}
            for n, lab in mj.items():
                if n not in seen:
                    seen[n] = [RUBY.sub("", lab), me.get(n, "")]
                elif not seen[n][1] and me.get(n):
                    seen[n][1] = me[n]

    missing = sorted(set(seen) - set(FR))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("id\tja\ten\tfr\tnote\n")
        for n in sorted(seen):
            ja, en = seen[n]
            note = "EN_SWAPPED" if n in EN_SWAPPED else ""
            f.write(f"{n}\t{ja}\t{en}\t{FR.get(n, '')}\t{note}\n")

    print(f"{len(seen)} tips terms -> {OUT}")
    print(f"french coverage: {len(seen) - len(missing)}/{len(seen)}")
    if missing:
        print("MISSING french for ids:", missing)


if __name__ == "__main__":
    main()
