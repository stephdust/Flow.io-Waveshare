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

## Température extérieure sur l'écran 480×320

L'ESP32 envoie déjà `globals.vaWaterTemp.txt` et `globals.vaAirTemp.txt`.
La Home utilise désormais les deux champs natifs `tWaterTemp` (eau, haut)
et `tAirTemp` (air extérieur, bas) dans le bandeau x=154..300.
Deux petites icônes goutte et soleil/nuage sont dessinées une seule fois
dans l'atlas (sans animation supplémentaire). Le champ `tAirTemp` est
ajouté **après tous les anciens composants** pour ne pas déplacer leurs IDs.

Les valeurs sont mises à jour dans `bUpdateGauge.down` et redessinées
à chaque `pageHome.loadend` après réveil. Vérifier la lisibilité et
l'absence de recouvrement par la date et l'heure sur le vrai Nextion.
Le test `nextion/scripts/test_nextion_outdoor_temp.py` est lancé par
`pio run` / `pio run -e nextion` avant la compilation nxwright.

## Atlas compact

Le fond est devenu uni, et l'atlas passe de 1035×1160 à **1035×728**
pixels. Les 55 images de turbine complètes ont été remplacées par cinq
couronnes PSI 70×70 et onze cœurs animés 42×42. Les coordonnées
`xpic` sont mises à jour ensemble avec `render_nx_home.py`. Le
test `nextion/scripts/test_nextion_animation.py` contrôle ce contrat.

## Touches Home alignées sur les dessins (sans bouton lecture)

Le bouton « lecture » a été retiré : il doublonnait inutilement la commande
de la pompe de filtration au centre de l'écran. Son dessin, sa zone `m2`
et son événement ont été supprimés. La grille de configuration est
recentrée dans la zone libérée ; les autres icônes restent inchangées.

| Icône | Composant | Zone (x, y, largeur, hauteur) | Action |
|---|---|---|---|
| Grille (en bas à gauche) | `b0` | `64,268,72,45` | Configuration |
| Turbine centrale | `m1` | `207,210,70,70` | Basculer la filtration |
| Engrenage (en bas à droite) | `m0` | `309,268,78,45` | Commandes des équipements |
| Alarme (à droite) | `b1` | `412,268,62,45` | Alarmes |

Ce sont des zones tactiles transparentes, sans fond opaque : les icônes
restent visibles. Les rectangles ne se chevauchent pas et les composants
d'état sont positionnés au-dessus du bandeau, pour éviter de cacher les
dessins ou de voler les appuis. Les identifiants des composants historiques
sont préservés (le composant `m2` était ajouté en dernier et a été retiré).

Le test `nextion/scripts/test_nextion_footer_touch.py` est intégré au
build et vérifie géométrie, actions et absence de bouton redondant.
La vérification tactile définitive reste à effectuer sur l'écran réel.

## Points à valider physiquement

Le réveil Nextion recharge `pageHome` (page 1) pour redessiner les jauges
`xpic`, puis `wup=255` est restauré en quittant la page. La pompe
tourne grâce à **11 petits centres de turbine centrés** (dont un fixe)
dessinés par `xpic`, indépendamment des **5 couronnes de pression**, au
timer de 50 ms et au bit 0 de filtration. À l'arrêt, l'image 0 reste immobile.
L'ancien composant `tProp` (police native `Propeller_50`) est conservé
pour compatibilité, mais masqué pour éviter son décalage graphique.

La compilation et les tests statiques ne remplacent pas la validation réelle :
vérifier les jauges, les transitions veille/réveil, les valeurs dynamiques,
l'animation de la pompe, le tactile et les messages série.

La branche sauvegardée `backup/nextion-v7-validated-20261127` reste disponible.
**Aucune modification des Nextion 5″/7″ ou de `christophebelmont/dev`.**

## Design 7.0.0 — corrections du bandeau et RSSI (27 novembre 2026)

- **Wi-Fi réel** : le firmware ESP32 encode le niveau RSSI de la station
  dans les bits `16..18` de `globals.vaStates`. Le HMI utilise cinq images
  colorées dans l'atlas (0 gris, 1 rouge, 2 ambre, 3 cyan, 4 vert).
  La connexion réseau et MQTT conservent leurs anciens bits 7 et 8.
- **Réveil** : le fond et les jauges `xpic`, la valeur de Wi-Fi et la turbine
  sont redessinés après le rechargement de `pageHome`.
- **Graphisme** : les capsules cyan superposées aux chiffres pH/ORP sont
  retirées ; la ligne parasite provoquée par le message d'alarme vide est
  supprimée ; les boutons du bas restent tactiles sans redessiner les
  rectangles opaques au-dessus des icônes ; les pales de pompe sont réduites
  de 28 % et restent animées.
- **Température/date** : textes plus compacts pour ne pas recouvrir le
  thermomètre et éviter le débordement sous le bandeau.
- **Compatibilité** : nouvelle variable `vaPrvWifiLevel` ajoutée **en fin**
  de liste des composants, sans décaler leurs identifiants.
- **Diffusion** : installer **le firmware ESP32 et le TFT 7.0.0 ensemble**
  pour activer le RSSI réel. Les autres Nextion restent inchangés.

Voir `scripts/tests/test_nextion_wifi_rssi.py` et
[`docs/integration/nextion-esp-protocol.md`](../../../../docs/integration/nextion-esp-protocol.md)
pour les seuils Wi-Fi.
