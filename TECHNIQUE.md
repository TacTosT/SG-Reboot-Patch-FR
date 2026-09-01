# Documentation technique

Comment le patch fonctionne : format des archives du jeu, dérivation de la clé
de déchiffrement, structure des dialogues, méthode de réinjection et modèle de
coût de la traduction.

Pour installer le patch, voir le [README](README.md).

STEINS;GATE RE:BOOT — Steam, AppID 4012810. Le projet fait suite à une
traduction du STEINS;GATE original et à une validation de la chaîne de
traduction sur un autre titre.

---

## 1. Le verrou : format MZS/PSB

Les données du jeu sont dans `wind3d11data/`, par paires `<nom>_info.psb.m`
(index) + `<nom>_body.bin` (contenu). Tout est empaqueté en **MZS** — XOR par
flux MT19937 puis compression Zstandard — un format du moteur M2 pour lequel
FreeMote indique qu'aucun déchiffrement n'est possible sans la clé du jeu.

### Clé retrouvée

```
seed    = Rk3nwA8ZYV0yV
keylen  = 131
clé     = seed + <nom d'entrée> [+ suffixe]
```

Trouvée par **attaque à clair connu**, sans désassembleur : après déchiffrement,
la charge utile doit commencer par le magic Zstandard `28 B5 2F FD`. Un XOR
contre le chiffré donne donc les 4 premiers octets du flux de clé — soit la
première sortie MT19937 — ce qui permet de tester des candidats extraits du
binaire du jeu à 32 bits de discrimination. La graine est tombée en 103 secondes
sur les suffixes de chaînes de `sgre_steam.exe`.

Vérifiée sur les **9** fichiers `*_info.psb.m` : tous produisent un magic `PSB\0`
valide.

### Convention de clé par archive

| Archive | Suffixe | Clé de l'entrée |
|---|---|---|
| `scenario` | `.scn.m` | `seed + nom + suffixe` |
| `script` | `.nut.m` | `seed + nom + suffixe` |
| `image`, `motion`, `config` | `.psb.m` | `seed + nom + suffixe` |
| `font` | `.psb.m` | `seed + nom` ← le nom porte déjà son extension |
| `sound`, `voice` | — | non chiffrées (`PSB\0` en clair) |
| `map` | — | archive vide |

`tools/sgre.py` essaie les deux formes, donc l'exception `font` est absorbée.

---

## 2. Structure du dialogue

Chaque `.ks` est un PSB v3 contenant un arbre de scènes. Le dialogue est dans
`scene["texts"]`, une entrée par réplique affichée :

```
[ locuteur, [variantes...], [voix...], index_ligne, mise_en_scène ]
```

`variantes[0]` est le **japonais original** ; les suivantes suivent la liste
`languages` du fichier, soit `["en", "tc", "sc"]`. Chaque variante est
`[locuteur, texte, longueur_affichée, *formes_alternatives]`.

**Le jeu embarque donc déjà l'anglais officiel**, ce qui donne une référence par
ligne — et un slot `en` où injecter le français, comme sur NEKOPARA.

`longueur_affichée` = longueur du texte **balises retirées** (à recalculer à la
réinjection).

### Volume

| | |
|---|---|
| Scripts scénario | 187 |
| Répliques | 24 795 |
| Caractères japonais | 574 364 |
| Répliques doublées | 14 468 |
| Locuteurs distincts | 146 |
| Répliques avec balises | 1 389 |

---

## 3. Balises à préserver

| Balise | Exemple | Règle |
|---|---|---|
| Pause | `%p-1;` `%p;` | verbatim, même nombre, même position |
| Saut de ligne | `\n` **littéral** | verbatim (26 lignes dans le prologue) |
| Tiret | `─` U+2500 | conserver, y compris en série |
| Tips | `<tips,8,ジョン・タイター>` | index inchangé, libellé traduit |
| Furigana | `[あご]顎` | lecture intraduisible → rendre le sens seul |
| Furigana sémantique | `[シュタインズゲート,4]運命石の扉` | **`N` = caractères couverts − 1** |

Le `N` du furigana sémantique est un index de fin base 0, vérifié sur toute la
distribution du corpus (115 occurrences) :
`迂闊`(2)→1, `大檜山`(3)→2, `運命石の扉`(5)→4, `時を超えた郷愁への旅路`(11)→10.

---

## 4. Deux découvertes qui valident le japonais comme source

**La localisation anglaise officielle contient des erreurs.** Cinq paires de
termes Tips y sont **interverties** :

| # | Japonais | Anglais officiel |
|---|---|---|
| 58 / 59 | ホコ天 / カメラ小僧 | "amateur photographers" / "Pedestrian Heaven" |
| 185 / 186 | スイーツ（笑）/ デコ電 | "deco phones" / "mainstream women" |
| 219 / 220 | 神経パルス / 側頭葉 | "Temporal Lobe" / "Nerve Impulses" |
| 225 / 226 | ＶＩＰ / 安価 | "anchors" / "VIP" |
| 267 / 268 | 薔薇十字軍 / 錬金術 | "Alchemy" / "Rosicrucian" |

Elle **déplace aussi du contenu entre lignes** et réécrit librement (ligne 22 du
prologue : 「聞くな。それがまゆりのためでもある」 devient "If I told you, I'd
have to kill you", qui n'existe pas en japonais).

Ces lignes portent la note `EN_SWAPPED` dans `prompt/tips_glossary.tsv`.

**Aucune contrainte de police.** Contrairement à SG1 (atlas bitmap, bidouille
PUA nécessaire), RE:BOOT embarque de vraies polices OpenType.
`hiragino_pro_w6.otf` — la police de dialogue — couvre l'intégralité du
français : accents, `ç`, `œ`, `æ`, `«  »`, et jusqu'à `Ÿ`.

---

## 5. Arborescence

```
sgreboot_fr/
├── tools/
│   ├── mzs.py              déchiffrement MZS (MT19937 + Zstandard)
│   ├── psb.py              lecteur PSB v2-v4 (trie de noms, arbre de valeurs)
│   └── sgre.py             accès archives (index + entrées)
├── prompt/
│   ├── system_fr.md        prompt système de traduction
│   ├── glossary_fr.md      terminologie, voix, tutoiement/vouvoiement
│   ├── tips_glossary.tsv   les 272 termes Tips du jeu (JA/EN/FR)
│   └── build_tips_glossary.py
├── extract_dialogue.py     extraction -> JSONL + texte lisible
├── translate.py            Batch API : estimate / submit / poll
├── validate.py             contrôle balises + complétude
└── extracted/              sorties
```

## 6. Utilisation

```bash
python extract_dialogue.py --list           # lister les 187 scripts
python extract_dialogue.py resg00_01.ks     # le prologue
python extract_dialogue.py --all            # tout le jeu

export ANTHROPIC_API_KEY=...
python translate.py estimate --file resg00_01.ks   # gratuit (count_tokens)
python translate.py submit   --file resg00_01.ks
python translate.py poll

python validate.py extracted/resg00_01.jsonl extracted/resg00_01_fr.jsonl
```

### Coût

Trois leviers multiplicatifs, mesurés sur le corpus réel :

| Levier | Effet |
|---|---|
| Batch API | −50 % sur tous les tokens |
| Prompt caching (préfixe 13 005 tokens) | −90 % sur prompt + glossaires |
| — | **36 $ économisés** sur le jeu entier |

Jeu entier sur Opus 5 à effort `high` : **~25 $** estimé hors thinking,
réalistement 40–60 $. L'effort n'est **pas** un levier de coût ici : le texte est
dense en jugement (registres Okabe/Kyouma, accord de Luka, argot 2chan), et
l'écart `high`→`low` ne représente qu'une trentaine de dollars sur tout le jeu.

### Garde-fou de complétude

Les sorties structurées imposent la **forme**, jamais la **complétude** — leçon
du run NEKOPARA. Un batch peut être « succeeded », renvoyer du JSON valide, et
omettre des lignes en silence. `translate.py poll` compare donc systématiquement
les identifiants rendus à ceux demandés et écrit les manquants dans
`*_missing.json` pour un second passage en chunks plus petits.

---

## 7. Réinjection — faite

Le français est écrit dans le **slot anglais** de chaque réplique : le slot
existe déjà, le moteur sait l'afficher, et aucune quatrième langue n'a besoin
d'être déclarée. **En jeu, mettre la langue sur English affiche le français.**

```bash
python inject.py --dry-run     # tout construire, ne rien écrire
python inject.py --apply       # patcher (sauvegarde vérifiée SHA256)
python inject.py --restore     # remettre les originaux
```

### Pourquoi pas d'encodeur PSB complet

L'ordre des sections est constant — `header | names | entries | str_offsets |
str_data | chunk_*` — donc l'arbre de valeurs (`entries`), la partie fragile
avec ses offsets relatifs internes, se trouve **avant** les chaînes et ne bouge
jamais. Les entries référencent les chaînes par **index**, pas par offset : à
nombre de chaînes constant, l'arbre reste valide tel quel. Seule la table de
chaînes est réécrite, les sections `chunk_*` glissent d'un delta connu, et
l'en-tête plus son Adler32 sont recalculés.

**Validé par round-trip sur les 182 fichiers**, réencodés avec leurs propres
chaînes et comparés octet par octet aux originaux : 182/182 identiques.

### L'index ne doit JAMAIS être réencodé

Pour l'index (`scenario_info.psb.m`), les offsets changent forcément. La
tentation est de réencoder son arbre `entries` avec `encode_value`. **Ne le
faites pas.** Le résultat est sémantiquement identique — `root`, `names`,
`strings`, `file_info` tous égaux — et le jeu charge quand même la plupart des
entrées à partir de là. Mais il échoue sur certaines, **sans le moindre
message** : la transition de scène retombe simplement à l'écran titre.

La cause : `encode_value` choisit la largeur d'octets **minimale** pour chaque
entier, alors que l'écrivain du jeu en élargit beaucoup — 61 offsets sur 4
octets là où 3 suffisent, 32 longueurs sur 3 là où 2 suffisent, et `version` en
flottant simple précision là où nous écrivions un double. Le format PSB est
pourtant auto-descriptif : chaque entier annonce sa largeur. Le moteur s'en
soucie quand même.

Isolé avec une seule variable : un corps d'archive copié bit pour bit de
l'original, accompagné du seul index réencodé **avec exactement les mêmes
valeurs**, reproduit le plantage à l'identique.

La bonne méthode est donc la même que pour les `.ks` : **écrire les nombres sur
place**, chacun conservant sa largeur d'origine (`IntRef.poke` dans
`tools/psb.py`). Les 374 entiers de `file_info` y tiennent. L'index patché fait
exactement la taille de l'original, et sur ses 894 octets qui diffèrent, 894
sont à l'intérieur d'un entier de `file_info`.

Le même principe s'applique à `display_length` dans les scénarios : sur les 175
fichiers modifiés, les 23 539 octets qui diffèrent de l'original sont **tous**
dans un entier `display_length`. Aucun octet de structure ne bouge nulle part.
C'est le contrôle à relancer après toute modification de la chaîne d'injection.

### Résultat

| | |
|---|---|
| Scénarios patchés | 175 |
| Entrées copiées verbatim | 12 (5 non-`.ks` + 7 fichiers de test) |
| Répliques injectées | 23 898 |
| Slots partagés | 144 — affichent déjà un anglais identique aujourd'hui |
| `scenario_body.bin` | 24 454 212 → 23 727 384 o (−3,0 %) |

Les entrées non-`.ks` sont recopiées comme **octets déjà compressés**, jamais
recompressées : elles ne peuvent donc pas être corrompues.

## 8. Distribution — `installer/`

Le patch se donne à quelqu'un d'autre sous la forme d'un seul `.exe` (13 Mo,
aucune installation de Python requise) : `installer/dist/`.

```
installer/
  patcher.py          interface Tk (installer / restaurer) + mode ligne de commande
  sgre_patch/
    mzs.py            MT19937 en Python pur — keystream identique à numpy,
                      vérifié sur plusieurs clés et longueurs (numpy en moins,
                      c'est 13 Mo d'exe au lieu de ~60)
    psb.py            copie de tools/psb.py
    psb_write.py      copie de tools/psb_write.py
    patch.py          build / install / uninstall, sans argparse ni chemin en dur
    locate.py         détection Steam (registre, libraryfolders.vdf, appmanifest)
  data/all_fr.jsonl   les 24 795 répliques françaises — seul contenu redistribué
  build_exe.py        génère l'icône, l'exe PyInstaller et le zip
  LISEZMOI.txt        mode d'emploi joueur
```

**Aucun fichier du jeu n'est redistribué** : l'exe reconstruit
`scenario_body.bin` à partir de l'installation du destinataire.

### Ce que l'installeur fait de plus qu'`inject.py`

- **Trouve le jeu tout seul** — registre Steam, bibliothèques secondaires
  (`libraryfolders.vdf`), `appmanifest_4012810.acf` si le dossier a été renommé.
- **Sauvegarde dans le jeu**, pas dans le dépôt : `wind3d11data/_fr_backup/`
  (+ `patch_fr.json` qui note les SHA-256 d'origine et patché).
- **Idempotent** : à la réinstallation il repart de la sauvegarde, jamais des
  fichiers déjà patchés.
- **Détecte une mise à jour du jeu** : si les fichiers ne correspondent plus à
  la sauvegarde ni au patch connu, la sauvegarde est refaite avant d'écrire —
  sinon une réinstallation réintroduirait silencieusement les scénarios de la
  version précédente.
- **Refuse de sauvegarder un fichier déjà français** : si la reconstruction
  redonne l'octet pour octet ce qui est déjà sur le disque, c'est que le patch
  est posé et qu'il n'y a pas d'original à conserver — renvoie vers la
  vérification d'intégrité Steam.
- **Écriture atomique** (`.fr_tmp` puis `os.replace`) : un plantage en cours
  d'écriture ne laisse pas un `body.bin` à moitié écrit.

### Vérification

Reconstruit à partir des originaux de `backup/`, le résultat est **identique
octet pour octet** à ce qu'`inject.py` avait posé dans le jeu
(`dec0e2c9…` pour le body, `33dc6f66…` pour l'index) — MT19937 maison compris.
Le cycle installer / réinstaller / restaurer a été passé sur une copie de
travail, en ligne de commande puis à la souris sur l'exe final.

```
cd installer
python patcher.py                       # interface
python patcher.py --status --game-dir X # état sans rien écrire
python build_exe.py                     # exe + zip dans dist/
```

## 9. Reste à faire

- [ ] **Test en jeu** — lancer, mettre la langue sur English, vérifier le rendu
      (retours à la ligne, débordements de boîte, accents).
- [ ] Relecture humaine des 115 furigana sémantiques.
- [ ] Les 144 slots partagés mériteraient un encodeur PSB complet (ajout de
      chaînes + réécriture des index dans l'arbre) pour donner un texte distinct
      à chacun. Gain : 0,6 % des lignes.
