# STEINS;GATE RE:BOOT — Traduction française

**Traduction française complète et non officielle de STEINS;GATE RE:BOOT (Steam).**

Traduite depuis le **japonais d'origine**, l'anglais officiel n'ayant servi que
de référence — et il fallait s'en méfier : la localisation anglaise intervertit
cinq paires de termes Tips et déplace du contenu d'une réplique à l'autre.

| | |
|---|---|
| Répliques traduites | **24 795** |
| Scripts | **187** — le jeu entier |
| Version | **1.1** |

---

## Installation

**[⬇️ Télécharger `Patch_FR_SteinsGate_ReBoot.exe`](../../releases/latest)**

1. **Lancez l'exe.** Windows affichera peut-être un avertissement SmartScreen —
   le programme n'est pas signé. *Informations complémentaires* → *Exécuter
   quand même*.

2. **Le dossier du jeu est trouvé automatiquement.** Sinon, *Parcourir…* et
   choisissez le dossier `SGRE` (celui qui contient `sgre_steam.exe`).

3. **Cliquez sur « Installer la traduction FR ».** Comptez une trentaine de
   secondes.

4. **Lancez le jeu et mettez la langue sur ENGLISH.**

> ### ⚠️ Oui, « English » — ce n'est pas une erreur
>
> La traduction occupe l'emplacement de la langue anglaise, qui existe déjà
> dans le moteur du jeu. Choisir *English* affiche donc le français. C'est ce
> qui permet au patch de fonctionner sans modifier une seule ligne du
> programme.

### Désinstallation

Le bouton **« Restaurer l'original »** remet tout en place. Vos fichiers
d'origine sont conservés dans `wind3d11data\_fr_backup` — ne supprimez pas ce
dossier. Si le jeu a été mis à jour depuis l'installation, le bouton est
désactivé (la sauvegarde date de l'ancienne version) : passez par Steam.

En cas de pépin, Steam sait tout réparer :
*clic droit sur le jeu → Propriétés → Fichiers installés → Vérifier l'intégrité*.

---

## Nouveautés de la version 1.1

Cette mise à jour corrige un **plantage bloquant**. Si vous avez la 1.0,
remplacez-la.

### 🛑 Le jeu revenait au menu titre au début du chapitre 1

Impossible d'aller plus loin. La cause n'était pas dans le texte mais dans la
façon dont le patch réécrivait l'index de l'archive du jeu : notre encodeur
choisissait la représentation la plus compacte pour chaque nombre, là où le jeu
en utilise une plus large. Le résultat était pourtant équivalent — le format
décrit lui-même la taille de chaque nombre — mais le moteur ne s'en accommode
pas. Il chargeait la plupart des scènes correctement, et échouait en silence
sur certaines.

Le patch ne reconstruit plus rien : il modifie les nombres **sur place**, chacun
gardant sa taille d'origine. Le fichier d'index fait désormais exactement la
même taille qu'avant, et sur les 894 octets qui changent, tous sont à
l'intérieur d'un nombre attendu.

### ✍️ Corrections d'affichage

- **Vitesse d'affichage du texte.** Chaque réplique stocke une longueur que le
  moteur utilise pour dérouler les caractères. Le patch laissait celle de
  l'anglais : sur plus de quatre répliques sur dix, le texte s'arrêtait trop tôt
  ou continuait dans le vide. Recalculée pour les 24 524 répliques concernées.

- **Historique des dialogues.** Le journal de lecture affichait encore l'anglais
  pour 1 440 répliques. Il est en français.

- **Un caractère qui s'affichait en case vide.** L'exposant de « 8ᵉ étage »
  n'existe dans aucune police du jeu. Remplacé partout par « 8e ».

- **Une annotation en ruby** dont la portée débordait sur la balise voisine.

### 📦 Archive plus légère qu'avant le patch

La compression utilisée ne correspondait pas à celle du jeu. Corrigée :
`scenario_body.bin` fait maintenant **727 Ko de moins que l'original**, au lieu
de 1,4 Mo de plus.

---

## Ce que le patch ne fait pas

- **Les menus, les Tips et les mails restent en anglais.** Seuls les dialogues
  sont traduits. Ces textes vivent dans une autre archive du jeu.
- **Les vidéos gardent leurs sous-titres anglais.** Ils sont incrustés dans
  l'image, pas superposés — les remplacer demanderait de réencoder les vidéos.

---

## Aucun fichier du jeu n'est redistribué

Le patch ne contient **aucune donnée de STEINS;GATE RE:BOOT**. L'exe embarque
uniquement le texte français, et reconstruit les fichiers du jeu à partir de
**votre propre copie**, sur votre machine. Il faut donc posséder le jeu.

Ce dépôt suit la même règle : ni fichiers du jeu, ni polices, ni texte japonais
ou anglais d'origine. Voir `.gitignore`, qui documente chaque exclusion.

STEINS;GATE RE:BOOT est une œuvre de MAGES. / 5pb. / Nitroplus. Ce projet est
un travail de fan, sans but lucratif et sans lien avec les ayants droit.

### Licence

Le **code** de ce dépôt — outillage MZS/PSB, extraction, réinjection,
installeur, scripts — est sous [licence MIT](LICENSE). Reprenez-le, adaptez-le
à un autre jeu du même moteur, il est fait pour ça.

Le **texte de la traduction** (`extracted/all_fr.jsonl`) n'est pas couvert par
cette licence et ne peut pas l'être : c'est une œuvre dérivée du scénario de
STEINS;GATE RE:BOOT, dont les droits appartiennent à ses ayants droit. Il est
mis à disposition pour un usage personnel, avec une copie légitime du jeu.

Aucune licence ne peut être accordée sur les données du jeu — et il n'y en a
aucune ici.

---

## Pour les curieux et les développeurs

Le format des données du jeu (MZS/PSB) n'est pas documenté publiquement et sa
clé de déchiffrement n'était pas connue. Elle a été retrouvée par attaque à
clair connu, sans désassembleur.

- **[`TECHNIQUE.md`](TECHNIQUE.md)** — format des archives, dérivation de la
  clé, structure des dialogues, balises à préserver, méthode de réinjection,
  modèle de coût de la traduction.
- **[`debug/CRASH_CH1.md`](debug/CRASH_CH1.md)** — le journal complet de la
  traque du plantage de la 1.0 : douze essais en jeu, les hypothèses écartées
  et pourquoi. ⚠️ *Contient des extraits de dialogue du chapitre 1.*

```bash
python extract_dialogue.py --all     # extraire les dialogues
python translate.py submit           # traduire (API Batch)
python validate.py <src> <fr>        # contrôler balises et complétude
python check_fr.py                   # contrôler la traduction seule (sans le jeu)
python inject.py --apply             # patcher (sauvegarde vérifiée SHA-256)
python inject.py --restore           # tout remettre en place
```
