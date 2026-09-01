# Bug : retour au menu titre au début du chapitre 1

> ## ⚠️ Avertissement — extraits de dialogue
>
> Ce document cite des répliques du **prologue et du chapitre 1** pour situer le
> plantage, et plusieurs scripts d'analyse en affichent d'autres dans leurs
> exemples. Si vous n'avez pas encore joué, passez votre chemin : le reste du
> dépôt ne dévoile rien.

## ✅ RÉSOLU — 2026-09-01

**Cause : l'index de l'archive était ré-encodé au lieu d'être modifié sur place.**

`psb_write.rebuild_entries` choisit la largeur d'octets **minimale** pour chaque
entier. L'écrivain du jeu, lui, en élargit beaucoup : dans `scenario_info.psb.m`,
**61 offsets sur 4 octets** là où 3 suffisent, **32 longueurs sur 3** là où 2
suffisent, et `version` en flottant simple précision (0x1E) là où nous
écrivions un double (0x1F). 93 octets économisés moins 4 repris : les 89 octets
d'écart mesurés, au bit près.

Le format PSB est auto-descriptif — chaque entier annonce sa largeur — donc le
moteur *devrait* s'en moquer. Il ne s'en moque pas : il chargeait la plupart
des entrées et échouait silencieusement sur d'autres, en retombant au titre.

**Prouvé avec une seule variable** : corps d'archive copie bit pour bit de
l'original, index ré-encodé avec **exactement les mêmes valeurs** → même
plantage. C'est le seul test qui isolait vraiment l'index.

**Correction** : ne plus jamais reconstruire l'arbre de l'index. Les offsets et
longueurs sont écrits **sur place** via `IntRef.poke`, chacun gardant sa largeur
d'origine. Vérifié au préalable que les 374 valeurs y tiennent. Appliqué à
`inject.py`, `installer/sgre_patch/patch.py` et `debug/tools/splitbuild.py` ;
`rebuild_entries` porte désormais un avertissement en tête.

**Vérification finale** : l'index installé fait la même taille que l'original,
même en-tête, mêmes noms, mêmes chaînes ; sur 894 octets différents, 894 sont
dans un entier de `file_info`. Et sur les 175 `.ks` modifiés, les 23 539 octets
qui diffèrent sont **tous** dans un entier `display_length`. Zéro octet de
structure déplacé dans tout le patch.

**Corrigé au passage** : la compression zstd était au niveau 12 alors que le jeu
utilise ~19. Le patch gonflait l'archive de 1,47 Mo ; il la réduit maintenant de
727 Ko (23 727 384 octets contre 24 454 212).

---

Ce qui suit est le journal de l'enquête, conservé pour la méthode et pour les
faits qu'il établit sur le moteur.

---


Journal de débogage. **Rien de ce qui est marqué ✅ ne doit être refait.**
Dernière mise à jour : 2026-08-31, ~22h30.

---

## 1. Le symptôme

Au chapitre 1, juste après la réplique `resg01_01.ks:*start:110` :

> « Ce qui me revient naturellement à l'esprit, c'est la scène surnaturelle
> d'il y a une heure`%p-1;─%p;─` »

le jeu **revient à l'écran titre**. Ce n'est pas un plantage :

- le processus `sgre_steam.exe` **ne se ferme pas** — l'utilisateur le ferme ensuite à la main ;
- **aucun dump WER**, **aucun événement « Application Error »** ;
- le moteur **ne journalise rien** au moment du retour au titre.

C'est donc un chemin **volontaire** du moteur (vraisemblablement une
`GameStateException`, cf. `script/exception` et `script/envplayer`).

#110 est la **dernière** réplique de `resg01_01.ks` (le fichier a 111 textes,
indices 0 à 110). Le `nexts` de la scène pointe sur `resg01_02.ks` (le
flashback, 92 textes). Le plantage a donc lieu **sur la transition**, avant que
la première réplique du flashback ne s'affiche.

La réplique est **unique dans tout le jeu** (vérifié en JA, EN et FR) : on est
bien au bon endroit. ✅

---

## 2. État de la machine — ⚠️ HISTORIQUE (soirée du 31/08)

Depuis, le patch corrigé est installé. Les empreintes ci-dessous sont celles
des builds de bissection, conservées pour la traçabilité.

**Installé dans le jeu** — le build `b_compl` du §4, prêt à être testé.
Ce n'est PAS le patch normal :

```
scenario_body.bin      1ad3c36465406aee86ea6d34…   (copie durable dans debug/builds/)
scenario_info.psb.m    ba8b123f6024d00754d773f7…
```

L'utilisateur n'a qu'à lancer le jeu et refaire le passage. Le build est
sauvegardé dans `debug/builds/` : il suffit de recopier les deux fichiers dans
`wind3d11data/` s'il a été écrasé.

**Références :**

| Fichier | SHA-256 (début) |
|---|---|
| `backup/scenario_body.bin` (original) | `b2ea22c0b906ed39…` |
| `backup/scenario_info.psb.m` (original) | `85803a0a83b19387…` |
| `extracted/all_fr.jsonl` (traduction corrigée) | `70ddea62c52374df…` |
| patch FR complet corrigé (build du 31/08) | `af6aa07ea2061e38…` |

**Pour remettre le patch français complet :**

```bash
cd /c/Users/valen/sgreboot_fr
python inject.py --restore && python inject.py --apply
```

⚠️ Le jeu doit être **fermé** avant toute écriture. Vérifier avec :
`Get-Process -Name sgre_steam -ErrorAction SilentlyContinue`

⚠️ `_fr_backup/patch_fr.json` dans le dossier du jeu porte encore le
`patched_sha` du build `af6aa07e`. À remettre à jour si on réinstalle un autre
build (sinon le patcher GUI croira l'installation périmée).

**Sauvegarde utilisée pour les tests :**
`C:\Users\valen\Documents\My Games\mages_steam\STEINS;GATE REBOOT\<steamid>\`

- `data_001_0000.bin` — slot auto/quick, horodaté **20:54:09**, jamais réécrit
  dans **aucune** session (donc : il n'y a **pas** de sauvegarde automatique à
  cette transition — hypothèse du dépassement de tampon de sauvegarde
  éliminée ✅).
- `data_001_0006.bin` — réécrit à 21:55:53 pendant la session en anglais qui a
  fonctionné (l'utilisateur a sauvegardé au-delà du point de plantage).
- `data_000_0000.bin` — données système, réécrit à chaque fermeture.
- Les `meta_*.bin` sont des PSB v3 **en clair** (lisibles avec `tools/psb.py`).
  Les `data_*.bin` sont chiffrés, `CryptMagic = 0xCA2B7FB4`, **non cassé**.

---

## 3. Le journal de bissection — LE CŒUR DU DOSSIER

Chaque ligne = un lancement réel par l'utilisateur. **Ne pas refaire.**

| # | Build | `resg01_01` | `resg01_02` | Reste | Résultat |
|---|---|---|---|---|---|
| 1 | patch FR complet corrigé `af6aa07e` | FR | FR | FR | 💥 plante |
| 2 | `line110` `e01fd932` | FR sauf #110 en EN | FR | FR | 💥 plante |
| 3 | **original intact** `b2ea22c0` | EN | EN | EN | ✅ **fonctionne** |
| 4 | `b_02en` `0d03f44c` | FR | **intact** | FR | 💥 plante |
| 5 | `b_markup` `b7f30666` | FR sauf ses 15 lignes à balise | FR | FR | 💥 plante |
| 6 | `b_01en` `83ad910c` | **intact** | FR | FR | 💥 plante |
| 7 | `b_early` `2e63340f` | **intact** | **intact** | FR (`resg00_01` et `resg01_03` intacts aussi) | 💥 plante |
| 8 | `b_late` `cf503a84` | FR | FR | ch. 6→11 **intacts**, ch. 0→5 + fichiers de test FR | 💥 plante |
| 9 | `b_compl` `1ad3c364` | **intact** | **intact** | ch. 0→5 **intacts**, ch. 6→11 FR | 💥 plante |
| 10 | patch FR, zstd niveau 19 (archive **plus petite** que l'originale) | FR | FR | FR | 💥 plante |
| 11 | `b_idxonly` — corps **copie bit pour bit** de l'original, index seul ré-encodé | EN | EN | EN | 💥 **plante → coupable isolé** |
| 12 | patch FR, index modifié **sur place** | FR | FR | FR | ✅ **fonctionne** |

L'utilisateur a confirmé à la manche 6 que **la langue affichée correspondait
bien au build** (anglais là où attendu) : les builds prennent donc bien effet.
✅

### Ce que le journal établit

1. **Le patch est en cause** (manche 3 : l'original fonctionne avec la même
   sauvegarde). Ni le jeu, ni la sauvegarde, ni le matériel.
2. **Ce n'est pas le texte affiché.** Manche 7 : les quatre fichiers du
   voisinage sont octet pour octet identiques à l'original et ça plante quand
   même.
3. **Ce n'est pas dans les chapitres 6→11** (manche 8).

### ⚠️ Le raisonnement à ne PAS tenir tel quel

En croisant 7 et 8, on serait tenté de conclure : « le coupable est un fichier
des chapitres 0→5, hors des quatre déjà innocentés », soit **88 fichiers** :
`resg01_04`→`resg01_13` (10), `resg02_*` (18), `resg03_*` (14), `resg04_*` (25),
`resg05_*` (17), plus `_sample_sg.ks`, `sgre_test_bgm.ks`, `sgre_test_flow.ks`,
`sgre_test_phone.ks` (4).

**Cette conclusion suppose qu'un seul fichier est responsable.** Or rien ne le
prouve, et le fait qu'aucun retrait ciblé n'ait jamais rien changé suggère au
contraire un **effet global** (taille totale de l'archive, offsets, un
compteur…), auquel cas la bissection par fichier ne convergera jamais.

---

## 4. ⚠️ HISTORIQUE — l'étape qui a résolu l'affaire

Ce contrôle a bien été joué le 01/09 : **il a planté**, ce qui a tué la
bissection et pointé vers l'index. Voir la section RÉSOLU en tête.

**Le contrôle complémentaire** — ✅ **DÉJÀ CONSTRUIT ET INSTALLÉ** (`b_compl`,
corps `1ad3c364…`). Il suffit de lancer le jeu et de refaire le passage.

⚠️ **Relancer la capture de logs AVANT que le jeu ne démarre** — elle s'arrête
avec la session Claude Code, donc elle ne tourne plus :

```bash
cd debug/tools && python dbwin.py sgre.log &     # en arrière-plan
```

Sans elle on perd la trace moteur du test. La capture doit être active avant le
lancement du jeu, sinon les objets `DBWIN_*` n'existent pas et le moteur écrit
dans le vide.

C'est **l'exact complément de `b_late`** : chapitres 0→5 + les 4 fichiers de
test **intacts**, chapitres 6→11 **en français**. Vérifié : `resg00_01`,
`resg01_01`, `resg01_02`, `resg05_17`, `sgre_test_phone` intacts ;
`resg06_01`, `resg11_08` en français.

Pour le reconstruire au besoin :

```bash
python splitbuild.py b_compl $(tr '\n' ' ' < debug/tools/half_early.txt)
```

C'est plus informatif qu'une manche de bissection de plus.

- **Si ça fonctionne** → un seul fichier des chapitres 0→5 est bien
  responsable, la bissection est valide, on continue par moitiés sur les 88
  candidats (≈7 manches).
- **Si ça plante aussi** → un ensemble **et** son complément plantent tous les
  deux, donc **aucun fichier n'est individuellement responsable**. C'est un
  effet global. La bissection est alors le mauvais outil et il faut attaquer
  par : taille totale de `scenario_body.bin` (24 454 212 octets à l'origine
  contre ≈25 927 546 patché), offsets des entrées, ou un compteur global.
  Piste concrète à tester dans ce cas : construire un patch français
  **volontairement raccourci** (tronquer chaque ligne FR à la longueur EN) pour
  que le corps garde une taille proche de l'original — si ça fonctionne, c'est
  la taille/les offsets.

---

## 5. Hypothèses éliminées (avec la preuve) — NE PAS REFAIRE ✅

**Intégrité de l'archive patchée**
- Les 187 entrées se déchiffrent, se parsent, et l'arbre PSB est identique à
  l'original entrée par entrée (`verify.py`, `audit_installed.py`) : 0 anomalie
  sur 24 524 lignes.
- Aucun slot japonais / chinois modifié.
- `rebuild_strings` rendu ses propres chaînes redonne le fichier **au bit
  près, 182/182** (`identity.py`). Le mécanisme de réécriture n'introduit rien.
- Aucun des 182 `.ks` ne contient de bloc de ressources (`chunks.py`) : le
  déplacement de la table de chaînes ne peut rien corrompre de ce côté.
- L'index reconstruit est **sémantiquement identique** à l'original : mêmes
  clés, mêmes types, mêmes chaînes, mêmes noms ; seuls les offsets changent
  (`idxdiff.py`).
- Les 795 transitions de scène du jeu pointent toutes vers une entrée existante,
  dans l'original **comme** dans le patch (`flowcheck.py`).

**Encodage**
- Largeur d'encodage des tableaux PSB : un seul fichier bascule de 2 à 3 octets
  à cause du français (`resg06_24s.ks`, bloc de chaînes 64 028 → 66 192, donc
  au-delà de 65 535). **Non pertinent** : le jeu d'origine utilise la largeur 3
  **1 116 fois**, `resg00_01.ks` compris (`widthcensus.py`). Le moteur la lit.
- Emballage MZS (`tools/mzs.py`) : structure correcte (`mzs\0` + uint32 taille
  décompressée + flux zstd XORé), et il fonctionne puisque le prologue
  s'affiche en français.
- Le champ `hash` (MD5) de chaque `.ks` **n'est pas recalculable** depuis le
  binaire (`hashtest.py` : ni le PSB en clair, ni le blob empaqueté, ni le nom,
  ni les sous-sections). C'est un artefact de compilation, le moteur ne peut pas
  le vérifier.

**Contenu du texte**
- Balisage comparé jeton par jeton avec la source japonaise pour `resg01_01` et
  `resg01_02` (`markupdiff.py`) : que des traductions légitimes, **aucune
  balise malformée**. Les deux balises `<tips>` de `resg01_02` sont **identiques
  à celles de l'anglais livré**.
- Aucun caractère invisible ou de contrôle dans toute la traduction
  (`charscan.py`).
- Les 67 rubis français : portées toutes dans les bornes après correction (voir
  §7). `rubycheck.py`.
- Volume de texte par scène (`volume.py`) : `resg01_01:*start` = 111 lignes /
  7 658 caractères FR, alors que `resg00_01:*dummy1` = 233 lignes / 13 965 et
  **passe**. Pas un débordement de tampon d'historique.
- Longueur des lignes : le prologue contient déjà une ligne de 194 caractères
  et passe. Ce n'est pas la longueur.
- Aucune particularité de `resg01_02` que le prologue et `resg01_01` n'aient
  déjà (`featdiff.py`).

**Ressources**
- Les 36 voix et 24 fichiers média de `resg01_02` (idem `resg01_01`,
  `resg01_03`) : **0 manquant, 0 illisible** (`res2.py`). Attention, les noms
  dans l'archive `voice` sont en **minuscules** (`resg01_02_oka0000`).
- Vérification d'intégrité Steam faite par l'utilisateur : aucun fichier
  manquant.

**Slots de chaînes partagés**
- 7 slots partagés entre langues, tous des numéros de post 2chan (`>>476`…),
  cosmétique (`shared.py`).
- Les 1 440 formes alternatives du slot EN ne sont partagées avec **rien**
  d'autre (`altshare.py`) : on peut les écraser sans risque.

**Recherche web** : aucun signalement comparable. Les fils techniques de
STEINS;GATE RE:BOOT sur Steam parlent de plantages **au lancement** et de voix
sous Linux. Rien sur un retour au titre en cours de partie.

---

## 6. Outillage (tout est dans `debug/tools/`)

Tout tourne avec **`C:/Users/valen/miniconda3/python.exe`** (c'est celui qui a
numpy / zstandard / PIL / PyInstaller). Toujours préfixer
`PYTHONIOENCODING=utf-8`, sinon la console cp1252 casse sur les caractères
japonais.

⚠️ **Piège du heredoc bash** : `<<'EOF'` mange les antislashs doubles. Tout
script manipulant `\n` littéral ou `\1` de regex doit être écrit avec l'outil
Write, ou utiliser `chr(92)`. Ça a déjà provoqué deux bugs (un fit de formule
faussé, et une règle de remplacement qui a supprimé du texte).

### `splitbuild.py` — l'outil de bissection

Reconstruit l'archive depuis `backup/` en laissant certaines parties en anglais.
Un fichier sans aucune traduction est laissé **octet pour octet identique à
l'original** (il n'est même pas réempaqueté).

```bash
python splitbuild.py OUTDIR resg01_02.ks               # fichier entier en EN
python splitbuild.py OUTDIR resg01_02.ks:0-45          # plage d'indices
python splitbuild.py OUTDIR resg01_01.ks:110           # une ligne
python splitbuild.py OUTDIR resg01_01.ks:%p            # ses lignes à code %p
python splitbuild.py OUTDIR resg01_01.ks:tips          # ses lignes à balise tips
```

Il retire aussi les lignes qui **partagent le même slot de chaîne**, sinon le
slot recevrait du français quand même et le test ne prouverait rien.

⚠️ Ne jamais nommer un script `bisect.py` : ça masque le module standard Python
et provoque une `RecursionError` à l'import.

Installation d'un build (jeu fermé) :
```bash
cp OUTDIR/scenario_body.bin   "/c/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data/"
cp OUTDIR/scenario_info.psb.m "/c/Program Files (x86)/Steam/steamapps/common/SGRE/wind3d11data/"
```

### `dbwin.py` — capture des logs du moteur

Le moteur écrit sur `OutputDebugString`. Le capteur doit tourner **avant** le
lancement du jeu :

```bash
python dbwin.py sgre.log      # à lancer en arrière-plan
```

Filtrer le bruit d'autres processus avec `grep -vE '\[12964\]'` (le PID varie).

**Lignes bénignes connues, à ignorer :**
- `AN ERROR HAS OCCURED [the index 'DialogWindow' does not exist]` à
  `rsc_project/script/tips.nut line [1533]` — au **démarrage**. Bug du jeu
  d'origine : `class TipsUnlockWindow extends DialogWindow`, et `DialogWindow`
  n'est défini que dans `script/debug`, absent en version commerciale.
- `cannot find file [config/op_subtitle.psb.m]` — le moteur cherche des
  sous-titres externes pour la vidéo d'ouverture. Le jeu n'en livre aucun.

Le moteur **journalise bien** les fichiers manquants et les exceptions Squirrel.
Le silence au moment du plantage est donc une information : ce n'est ni un
fichier manquant, ni une exception Squirrel non rattrapée.

### Autres scripts utiles

| Script | Ce qu'il fait |
|---|---|
| `audit_installed.py` | audite les fichiers réellement installés dans le jeu |
| `verify.py` / `verify2.py` | compare structurellement patch et original |
| `markupdiff.py <fichier>` | balisage JA vs EN vs FR, ligne par ligne |
| `dumpall.py <fichier>` | toutes les lignes FR d'un fichier avec leur longueur |
| `dump.py <fichier> <a> <b>` | JA / EN / FR sur une plage |
| `lines.py <fichier> <a> <b>` | la liste de commandes `lines` d'une scène |
| `sqstr.py --grep <regex>` | cherche dans les chaînes des scripts Squirrel compilés |
| `nut.py` | extrait les 72 entrées de l'archive `script` |
| `res2.py` | vérifie voix et média référencés par une scène |
| `fit3.py` | revalide la formule de `display_len` (100 % sur 98 367) |

---

## 7. Corrections déjà faites (et appliquées à `all_fr.jsonl`)

Elles sont **acquises** et **ne corrigent pas** le bug de ce dossier, mais elles
sont justes et doivent être conservées.

**1. `display_len` recalculée sur les 24 524 lignes.** Chaque variante de
réplique stocke une longueur d'affichage que `inject.py` ne recalculait jamais :
elles portaient encore la longueur de l'anglais. Formule retrouvée et validée
**100 % sur 98 367 échantillons** du jeu d'origine :

> retirer les codes `%[a-zA-Z]…;` ; retirer les crochets furigana
> `[lecture]` / `[lecture,N]` ; `\n` compte **0** ; tout autre `\X` compte
> **1** (le caractère échappé seul) ; les balises `<tips,N,…>` comptent
> **brutes**, balisage inclus.

Écrite **sur place** dans l'arbre PSB en conservant la largeur d'octets
d'origine (vérifié : les 24 524 valeurs y tiennent), donc l'arbre ne bouge pas.
Voir `IntRef.poke()` dans `tools/psb.py`.

**2. Les 1 440 formes alternatives** (variante sans `\n`, utilisée par le
backlog) étaient restées en anglais. Elles sont maintenant en français.

**3. `ᵉ` (U+1D49) → `e`**, 23 lignes. Ce glyphe n'existe dans **aucune** police
de dialogue du jeu (ni `hiragino_pro_w6`, ni les Source Han) — vérifié sur la
table cmap des 10 polices. Il s'affichait en case vide. Règle dans
`prompt/terminology_fixes.tsv`.

**4. Un rubis hors bornes**, `resg02_06.ks:*dummy5:10` :
`[Ragnarök,22]guerre sainte finale` — la portée de 22 caractères débordait de 3
sur le `>` fermant de la balise `<tips>` qui l'entoure. Corrigé en 19. Seul cas
sur 67. Règle dans `prompt/terminology_fixes.tsv`.

**Code modifié :** `tools/psb.py` (classe `IntRef`, paramètre `track_ints`),
`inject.py` (`display_len`, `flat_form`, `patch_one` qui renvoie maintenant 4
valeurs), `installer/sgre_patch/psb.py` et `installer/sgre_patch/patch.py`
(mêmes changements). Sortie de l'installeur vérifiée **identique octet pour
octet** à celle d'`inject.py`.

**⚠️ RESTE À FAIRE** une fois le bug résolu : recopier
`extracted/all_fr.jsonl` dans `installer/data/` puis
`cd installer && python build_exe.py` pour régénérer l'exe distribuable.
**Pas encore fait.**

---

## 8. Pistes encore vivantes

1. **Effet global lié à la taille ou aux offsets de l'archive.** C'est la piste
   n°1 après le contrôle du §4. Le corps passe de 24 454 212 à ≈25 927 546
   octets.
2. **Un balayage global de l'archive à cette transition.** Le moteur a un
   système de cache (`addCache`, `addCacheRaw`, `addCacheBinary`,
   `isWaitCache` dans `script/savesystem`) et un système de « flow »
   (`script/flow`, `tag_resg_flow`). Si l'un des deux parcourt toutes les
   entrées à cette transition, un fichier lointain peut faire tomber la scène.
3. **Les Tips.** L'utilisateur a remarqué que « plusieurs TIPS apparaissent » à
   ce moment-là. `resg01_02.ks` enregistre les Tips 24, 25 et 26 dans ses
   lignes 8/9/10, **avant** la première réplique. Le moteur a un filtre
   `textFilterTips` (dans `script/override`) appliqué au texte. Hypothèse non
   vérifiée : s'il cherche le **nom du Tips dans la langue courante** — donc les
   noms anglais, puisque `config/tips.psb` n'est pas traduit — il chercherait
   « Lab » à l'intérieur du texte français et le trouverait dans « labo »,
   « laboratoire ». À creuser en désassemblant `override` / `tips`.
4. **L'archive `config` non traduite.** `text`, `tips`, `chrname_list`,
   `maildata`, `medal`, `moviemode`, `musicmode` sont restés en anglais. Si le
   moteur croise ces tables avec le texte des scènes, il y a là une
   incohérence structurelle FR/EN.

---

## 9. Contexte à ne pas reperdre

- Le français est injecté dans le **slot anglais**. En jeu, mettre la langue sur
  **English** affiche le français.
- Structure d'une réplique : `[locuteur, [variantes…], [voix…], index, mise en scène]`,
  `variantes[0]` = japonais, puis `["en","tc","sc"]`. Chaque variante :
  `[locuteur, texte, longueur_affichée, *formes_alternatives]`.
- Le slot anglais livré ne contient presque **aucun** balisage : 2 `%p` dans
  tout le jeu et **zéro** rubi, alors qu'on y injecte 2 182 `%p` et 67 rubis.
  1 074 lignes gagnent du balisage là où la variante EN n'a **aucune** forme
  alternative. Le prologue en contient et fonctionne — donc ce n'est pas fatal
  en soi, mais c'est la différence structurelle la plus marquée entre l'anglais
  livré et ce qu'on écrit.
- Les entrées `charvoice`, `classlist`, `filelist`, `scenelist`,
  `standposition` et `_regist_*.ks` ne sont **jamais** modifiées par le patch.
  `scenelist` contient un `textCount` par scène — on ne change jamais le nombre
  de répliques, donc rien à recouper.
- Les 4 fichiers non-scénario qui **reçoivent** du français :
  `sgre_test_bgm.ks` (35), `sgre_test_flow.ks` (21), `sgre_test_phone.ks` (205),
  `_sample_sg.ks` (10). Ce sont des scénarios de test — candidats plausibles
  s'ils sont chargés par le moteur.
