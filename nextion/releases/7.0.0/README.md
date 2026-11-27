# Nextion flow.io — 7.0.0 (préparation)

> **État : en préparation — non installable.** Aucun fichier `.tft` de la version 7.0.0 n'est publié dans ce dossier. Ne pas modifier `TFT_FIRMW` / `nextion_firmware_version` tant que les trois TFT n'ont pas été compilés, contrôlés et testés.

## Modèles prévus

| Modèle | Taille | Résolution | Source | TFT attendu |
|---|---|---|---|---|
| NX4832K035_011 | 3,5″ | 480 × 320 | HMI 3,5″ à intégrer | `FlowIO_Nextion_NX4832K035_011-7.0.0.tft` |
| NX8048P050-011R | 5,0″ | 800 × 480 | HMI à adapter | `FlowIO_Nextion_NX8048P050_011-7.0.0.tft` |
| NX8048P070-011R | 7,0″ | 800 × 480 | HMI à adapter | `FlowIO_Nextion_NX8048P070_011-7.0.0.tft` |

Les définitions 5″ et 7″ ont la même résolution, mais leurs firmwares restent propres à chaque modèle. Ne jamais renommer un TFT d'un modèle en un autre.

## Évolutions prévues

- Bandeau supérieur : logo flow.io à gauche, date `JJ/MM/AA` et heure `HH:MM` au centre, état Wi-Fi à droite ; disposition à vérifier sur l'écran réel.
- **Heure uniquement** : contrôle toutes les 10 secondes, sans lecture NTP supplémentaire ; envoyer `tTime.txt` seulement si `HH:MM` a changé (ou après réveil / reconnexion). Source : heure locale de Flow.io (NTP/RTC), selon le contrat existant.
- **Date** : format compact `JJ/MM/AA`, actualisation au changement de jour et après réveil ; conserver la logique RTC Nextion existante jusqu'à adaptation validée de l'HMI.
- **Wi-Fi** : mises à jour uniquement sur changement d'état, sans imposer de cadence de 10 secondes.
- **Jauges, mesures et autres éléments** : conserver leurs cadences de mise à jour existantes, sans rafraîchissement global de l'écran toutes les 10 secondes.
- Reconstruction explicite des jauges graphiques de la page principale après réveil du Nextion (diagnostic et correctif à valider).
- Adaptation des ressources et placements pour NX4832K035_011 et NX8048P070-011R, sans perdre les fonctions existantes.
- Préserver les traitements d'événements tactiles, identifiants de composants et commandes série compatibles avec le firmware Flow.io ; toute modification du protocole nécessite sa prise en charge côté ESP32-S3.

## Publication

1. Ajouter les fichiers sources `.HMI` éditables, issus des projets Nextion Editor et vérifiés.
2. Appliquer les changements d'interface et de logique, puis compiler chaque cible avec Nextion Editor.
3. Vérifier que le contrôle d'heure à 10 s n'entraîne pas de transmissions redondantes ni de rafraîchissement global ; vérifier minuit et sortie de veille.
4. Vérifier la compilation des trois modèles et nommer les TFT selon la convention ci-dessus.
5. Tester l'affichage, les commandes tactiles, le bandeau, la langue, le réveil et la mise à jour Nextion sur matériel.
6. Seulement après validation, basculer `common.nextion_firmware_version` de `6.0.0` à `7.0.0` dans `platformio.ini` et contrôler le contenu de `binary/` ainsi que le manifeste OTA.

La présence de ce dossier ne constitue ni une release stable ni une mise à jour prête au déploiement.
