# Nextion flow.io 7.0.0 — NX4832K035_011 (480 × 320)

> **État : travaux préparatoires, pas encore de HMI 7.0.0 modifié ni de TFT 7.0.0 compilé.**
> La version 6.0.0 reste seule publiée et installable ; ne pas modifier `common.nextion_firmware_version` dans `platformio.ini`.

## Périmètre validé

- **Écran unique pour cette étape :** Nextion Enhanced `NX4832K035_011`, 3,5″ (appelé parfois 4″), 480 × 320.
- Source de référence existante : [Flowio_Enhanced_480x320.HMI (6.0.0)](../6.0.0/Flowio_Enhanced_480x320.HMI).
- **Les modèles 5″ et 7″ sont hors périmètre** : aucun HMI/TFT n'est modifié pour eux dans cette étape.
- Conserver tous les noms de variables, IDs d'objets, gestion des pages, codes d'actions et messages série déjà utilisés par le firmware Waveshare.

## Changements UI à effectuer dans Nextion Editor

1. Sur la page Home, réorganiser **seulement le bandeau** : logo flow.io à gauche, date `JJ/MM/AA` et heure `HH:MM` au centre, état Wi-Fi à droite. Vérifier la lisibilité à **480 × 320** et les éventuels recouvrements.
2. Préserver la variable / l'objet `tTime.txt` déjà alimenté par l'ESP ; ne pas le renommer sans modifier simultanément le firmware.
3. L'heure est affichée au format `HH:MM`, **mise à jour au changement de minute** (contrôle au plus une fois par minute, ou immédiatement au réveil / reconnexion). Pas de mise à jour toutes les 10 secondes.
4. La date est affichée `JJ/MM/AA` et ne change qu'à minuit (ainsi qu'à l'initialisation et au réveil) ; conserver la logique RTC existante, ou mettre à jour le protocole ESP/HMI de façon atomique si un nouveau champ global est ajouté.
5. Conserver le fonctionnement normal du Wi-Fi, des mesures et des jauges. **Ne pas abaisser la fréquence de rafraîchissement des jauges à une minute.**
6. Après réveil du Nextion, vérifier le rendu des jauges pH/ORP et restaurer leur représentation graphique si elle disparaît. S'appuyer sur le chemin existant de *FullRefresh* et éviter une nouvelle boucle permanente de redessin.
7. Conserver les événements tactiles, les valeurs `vapHPercent.val`, `vaOrpPercent.val`, `globals.vaStates.val` et le protocole `printh 23 ...`.

## Vérifications avant publication

- Compiler avec Nextion Editor **pour NX4832K035_011** et vérifier que la compilation n'émet aucune erreur.
- Tester l'affichage de la date, de l'heure, du Wi-Fi et des jauges au démarrage puis à la sortie de veille.
- Tester passage de minute, passage de minuit, heure NTP/RTC et reconnexion.
- Confirmer que les commandes tactiles et les événements de la page Home n'ont pas régressé.
- Confirmer les transferts OTA Nextion et la compatibilité modèle avant de renommer le binaire.
- Publier la source modifiée sous `Flowio_Enhanced_480x320.HMI` et le TFT compilé sous `FlowIO_Nextion_NX4832K035_011-7.0.0.tft`, **uniquement après ces contrôles**.
- Changer ensuite `common.nextion_firmware_version` dans `platformio.ini` et valider la génération de `binary/` / du manifeste.

Références : [protocole ESP/Nextion](../../../docs/integration/nextion-esp-protocol.md) · [documentation hardware](../../../docs/hardware/nextion-displays.md).
