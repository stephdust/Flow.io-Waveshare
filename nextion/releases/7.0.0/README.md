# Nextion Flow.io 7.0.0 — NX4832K035_011 (480 × 320)

> **Branche de travail : `stephdust/dev`.** La référence reste
> `christophebelmont/Flow.io-Waveshare:dev` jusqu'au PR.
> Les Nextion 5″ et 7″ sont inchangés.

Cette release contient le HMI et le TFT 7.0.0 compilés avec **nxwright**
depuis le projet éditable
[`nextion/tests/NX4832K035_011/7.0.0/source/`](../../tests/NX4832K035_011/7.0.0/source/).
Le HMI 7.0.0 qui fonctionnait précédemment reste sauvegardé dans la branche
`backup/nextion-v7-validated-20261127`. La release 6.0.0 reste conservée.

## Deux commandes PlatformIO

Depuis la racine du dépôt :

| Commande | Fonction |
|---|---|
| `pio run -e nextion` | Vérifie les sources, compile HMI et TFT avec nxwright, copie le TFT dans `binary/`, puis régénère `binary/manifest.json` |
| `pio run -e nextion -t manifest` | Sans compilation : copie le TFT existant dans `binary/` et régénère seulement `binary/manifest.json` |

La version reste `7.0.0`. Aucun build ESP32/SPIFFS pour ces deux commandes.
Le manifeste et le TFT doivent être publiés ensemble en cas de distribution HTTP.

## Diffusion HTTP et OTA Nextion 3,5″

Les commandes `pio run` (compilation complète) et `pio run -e nextion`
(compilation Nextion seule) génèrent le TFT et le manifeste dans le répertoire
**local** `binary/`. Elles ne publient pas ces fichiers sur un serveur HTTP
distant. Si le serveur est séparé, recopier ensemble :

- `binary/FlowIO_Nextion_NX4832K035_011-7.0.0.tft`
- `binary/manifest.json`

La commande vérifie désormais que le manifeste référence ce TFT avec le bon
nom, le bon modèle, la bonne taille et le bon SHA-256.

**L'action « Vérifier les mises à jour » ne télécharge que le manifeste.**
Le fichier TFT est téléchargé **après** « Mettre à jour » et uniquement si le
modèle d'écran est compatible, l'opération acceptée et la PSRAM suffisante.
Si l'identité matérielle du panneau n'est pas lisible, l'interface propose
désormais une sélection manuelle explicite. Une identité connue mais
incompatible reste bloquée.

Avant de réessayer une mise à jour en échec, vérifier :

1. La réponse de `/api/fwupdate/check` : `nextion.artifact_selected`,
   `nextion.compatibility` et `nextion.artifact_path`.
2. Les logs Web/ESP32 : un refus « no compatible nextion artifact selected »
   précède toute requête TFT ; une erreur « Nextion PSRAM insufficient
   (2 MiB reserve) » est également émise avant le téléchargement.
3. Le serveur HTTP : le `.tft` référencé doit être accessible dans le
   **même répertoire** que `manifest.json`, avec la même taille et le
   même SHA-256.
4. Si l'OTA est autorisée : surveiller les logs `[NEXTION-OTA]` ;
   `stage=psram_admission` indique l'espace libre et le plus grand bloc
   de PSRAM. L'UART n'est ouvert qu'après téléchargement et vérification
   intégrale du TFT en mémoire.

Ne pas contourner les contrôles de compatibilité ou la réserve PSRAM :
ils protègent l'écran d'une mise à jour partielle.

## Contrôles de non-régression

- Rafraîchissement au réveil : la page Home est rechargée pour redessiner le
  fond et les deux jauges `xpic` (pH/ORP).
- Rotation de la pompe : `tmAnim` conserve sa période de 50 ms et le
  bit 0 de filtration. Les pales sont désormais de **vraies images animées**
  centrées : 10 images en marche, une fixe à l'arrêt, avec 5 couleurs
  selon l'état PSI. `tProp` et la police `Propeller_50` restent dans le
  projet mais l'ancienne représentation est masquée.
- Conserver les valeurs dynamiques, le protocole série, les commandes tactiles,
  les timers et les identifiants des composants.
- Vérifier après installation le Wi-Fi, la date/heure, les jauges,
  les changements de page et plusieurs cycles veille/réveil.

L'ancienne méthode d'analyse Nextion2Text et les patchs binaires `.pa/.i`
ne font **plus partie** de la chaîne de compilation. La validation automatique
nxwright est réussie, mais la validation matérielle finale est encore requise
avant tout PR vers Christophe.

Documentation : [Nextion](../../README.md) ·
[Tests et sources](../../tests/NX4832K035_011/7.0.0/README.md).

## Wi-Fi multicolore réel et retouches Home

La version Nextion 7.0.0 affiche maintenant **le vrai niveau RSSI transmis
par l'ESP32** (0..4, gris/rouge/jaune/cyan/vert) par le canal existant
`globals.vaStates`. Les anciens bits de connexion et MQTT sont conservés.
Les jauges n'ont plus de capsules blanches/cyan, le bandeau d'alarme vide
est masqué et l'icône de pompe conserve sa rotation avec des pales affinées.

**Attention :** pour ce changement RSSI, mettre à jour **Flow.io ESP32-S3 ET
Nextion TFT 7.0.0**. Le nouveau TFT seul ne reçoit pas le niveau de signal
si l'ancien firmware ESP32 est encore installé.

Le rendu matériel, le comportement après veille et la rotation en charge
restent à valider physiquement avant toute proposition de PR.
