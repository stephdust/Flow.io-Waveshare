# Laboratoire nxwright Nextion NX4832K035_011 / 7.0.0

Ce dossier conserve le **projet nxwright éditable** (`source/`) et la
prévisualisation (`preview.png`). Le projet vise uniquement le Nextion
`NX4832K035_011` 480 × 320.

La référence amont est `christophebelmont/Flow.io-Waveshare:dev` ;
nous développons et testons sur `stephdust/dev` avant tout PR.

## Méthode maintenue

Éditer `source/pages/pageHome.nx`, `source/pages/pageHome.page.toml` et,
si besoin, les ressources graphiques. Puis, depuis la racine :

```bash
pio run -e nextion             # HMI + TFT + manifeste
pio run -e nextion -t manifest # copie TFT existant + manifeste
```

La compilation nxwright est orchestrée par `nextion/scripts/run_nextion.py`.
Le rendu graphique Home est maintenu par
`nextion/scripts/render_nx_home.py` et les tests par
`test_nextion_wake.py` et `test_nextion_animation.py`.
Les HMI/TFT générés sont committés dans `nextion/releases/7.0.0/`.

## Points à valider physiquement

Le réveil Nextion recharge `pageHome` (page 1) pour redessiner les jauges
`xpic`, puis `wup=255` est restauré en quittant la page. La pompe
tourne grâce à **10 images de turbine centrées** dessinées par `xpic`, au
timer de 50 ms et au bit 0 de filtration. À l'arrêt, l'image 0 reste immobile.
L'ancien composant `tProp` (police native `Propeller_50`) est conservé
pour compatibilité, mais masqué pour éviter son décalage graphique.

La compilation et les tests statiques ne remplacent pas la validation réelle :
vérifier les jauges, les transitions veille/réveil, les valeurs dynamiques,
l'animation de la pompe, le tactile et les messages série.

La branche sauvegardée `backup/nextion-v7-validated-20261127` reste disponible.
**Aucune modification des Nextion 5″/7″ ou de `christophebelmont/dev`.**
