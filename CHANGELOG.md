# Journal des versions

Aucune entrée de ce fichier ne dévoile d'élément de l'histoire.

---

## Prochaine version — non publiée

Installeur plus sûr. La traduction ne change pas.

- **« Restaurer l'original » ne peut plus abîmer le jeu.** Après une mise à
  jour du jeu, la sauvegarde date de l'ancienne version : le bouton est alors
  désactivé, et l'installeur propose de réinstaller le patch.
- **Plus de jeu à moitié patché.** Les deux fichiers modifiés sont écrits en
  entier avant d'être mis en place, ensemble. Fermer la fenêtre pendant
  l'installation l'arrête proprement.
- **Message clair si l'écriture est refusée** (jeu ouvert, droits
  insuffisants), au lieu d'une « Erreur inattendue ».
- Petites corrections d'affichage dans la fenêtre (accents, couleur d'un
  bouton).

---

## 1.1 — 1er septembre 2026

Correction d'un plantage bloquant. **Si vous avez la 1.0, mettez à jour.**

### Corrigé

- **Le jeu revenait au menu titre au début du chapitre 1**, rendant la suite
  inaccessible.

  La cause n'était pas dans le texte traduit. En réécrivant l'index de
  l'archive du jeu, le patch encodait chaque nombre sur le plus petit nombre
  d'octets possible, alors que le jeu en utilise davantage : 61 positions sur
  4 octets là où 3 suffisent, 32 longueurs sur 3 là où 2 suffisent. Le format
  décrivant lui-même la taille de chaque nombre, le résultat aurait dû être
  équivalent. Le moteur ne s'en accommode pas : il retrouvait la plupart des
  scènes et échouait sur d'autres, sans message d'erreur.

  Le patch ne reconstruit plus l'index. Il écrit les nombres **sur place**,
  chacun conservant sa taille d'origine.

- **Vitesse d'affichage du texte** faussée sur 42 % des répliques. Chaque
  réplique stocke une longueur d'affichage que le patch laissait à sa valeur
  anglaise. Recalculée pour les 24 524 répliques concernées, d'après une règle
  déduite puis vérifiée sur les 98 367 variantes livrées avec le jeu.

- **Historique des dialogues en anglais** pour 1 440 répliques.

- **Caractère manquant** : l'exposant de « 8ᵉ » (U+1D49) n'existe dans aucune
  police de dialogue du jeu et s'affichait en case vide. Remplacé par « 8e »
  sur les 23 répliques concernées.

- **Annotation ruby hors bornes** dans une réplique, dont la portée mordait sur
  la balise voisine.

### Modifié

- **Compression alignée sur celle du jeu** (zstd niveau 19 au lieu de 12).
  `scenario_body.bin` passe de 24 454 212 à 23 727 384 octets, soit 727 Ko de
  **moins** que l'archive d'origine, au lieu de 1,4 Mo de plus.

### Vérifications ajoutées

- Contrôle octet par octet après injection : chaque octet qui diffère de
  l'original doit se trouver à un emplacement voulu. Sur les 175 fichiers
  modifiés, les 23 539 octets concernés sont tous à l'intérieur d'un nombre de
  longueur d'affichage ; dans l'index, les 894 octets sont tous à l'intérieur
  d'un nombre de position ou de taille. Aucun octet de structure ne bouge.

- L'exécutable distribué produit des fichiers **identiques au bit près** à ceux
  produits par la chaîne de développement, et donc à ceux effectivement testés
  en jeu.

---

## 1.0 — 24 août 2026

Première version publique.

- Traduction complète des dialogues : 24 795 répliques, 187 scripts.
- Traduite depuis le japonais d'origine.
- Installeur graphique autonome, sans Python à installer.
- Sauvegarde vérifiée des fichiers d'origine, restauration en un clic.
