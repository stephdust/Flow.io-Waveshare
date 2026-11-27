# Nextion NX4832K035_011 — laboratoire 7.0.0 sur le fork `stephdust/dev`

Ce dossier contient les **sources modifiables nxwright** et les diagnostics d'une version
graphique expérimentale du Nextion Enhanced `NX4832K035_011` (480 × 320).

La **référence amont est `christophebelmont/Flow.io-Waveshare:dev`**. Les modifications
sont développées et testées dans `stephdust/Flow.io-Waveshare:dev`, **sans PR pour le
moment**. Le modèle 5″ `NX8048P050_011` et le 7″ `NX8048P070_011` sont exclus.

## Génération reproductible

Le workflow [Nextion nxwright redesign](../../../../.github/workflows/nextion-nxwright-redesign.yml)
effectue les opérations :

1. Lire le HMI 7.0.0 fonctionnel sauvegardé sur
   `backup/nextion-v7-validated-20261127`.
2. `nxwright extract`, modifier les fichiers de la source extraite via
   `nextion/scripts/modernize_3p5_nxsource.py`, puis `nxwright check`.
3. `nxwright build` et réextraction pour vérifier le HMI.
4. `nxwright compile --download` pour générer un vrai TFT NX4832K035
   avec le firmware officiel de Nextion Editor 1.68.2.
5. Commiter sur **notre fork `dev` seulement** les sources éditables, la
   prévisualisation, le rapport de compilation, ainsi que les fichiers
   `FlowIO_Nextion_NX4832K035_011-7.0.0.HMI` et
   `FlowIO_Nextion_NX4832K035_011-7.0.0.tft` dans `nextion/releases/7.0.0/`
   pour les tests locaux.

`source/` contient les fichiers `app.toml`, `pages/*.nx`, `pages/*.page.toml`,
`pictures/` et `fonts/`. Le numéro de version reste strictement **7.0.0**.

**Important :** ce TFT est une version expérimentale sur notre branche `dev`.
La compilation nxwright réussie ne valide pas l'affichage physique, les jauges,
le retour après veille ou les événements série/tactiles. Aucun PR amont avant
validation matérielle. Les sources HMI fonctionnelles précédentes sont sauvegardées
sur la branche de référence `backup/nextion-v7-validated-20261127`.

## Correction de la veille — 7.0.0 (27/11/2026)

Home définit `wup=1` dans `pageHome.load` : après mise en veille, le Nextion
recharge la page physique 1 (Home) et réexécute les commandes `xpic` de
`pageHome.loadend` ainsi que l'invalidation du cache des deux jauges.
Sur `pageHome.unload`, `wup=255` restaure le comportement habituel des
autres pages. Le test `nextion/scripts/test_nextion_wake.py` vérifie ce
contrat. **Validation réelle après plusieurs veilles toujours requise.**
