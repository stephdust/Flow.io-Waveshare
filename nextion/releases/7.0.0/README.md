> **Release officielle 7.0.0 : HMI de référence remis à la dernière version validée sur écran réel.** L'essai de redesign par patch binaire a provoqué des rectangles blancs et a été retiré. Le nouveau HMI graphique expérimental est construit proprement depuis les **sources nxwright texte/PNG**, dans un [artefact distinct](https://github.com/stephdust/Flow.io-Waveshare/actions/runs/46004942701). **Ne pas utiliser les fichiers de test comme firmware de production tant que le rendu sur écran réel n'est pas validé.**

# Nextion flow.io 7.0.0 — NX4832K035_011 (480 × 320)

> **État : HMI original 7.0.0 validé restauré dans la release ; nouveau design expérimenté séparément via nxwright.**
> Version maintenue : `7.0.0`. La version 7.0.0 précédente, déjà compilée et testée sur matériel (jauges après veille OK), est conservée sur la branche [`backup/nextion-v7-validated-20261127`](https://github.com/stephdust/Flow.io-Waveshare/tree/backup/nextion-v7-validated-20261127). Ne pas installer le nouveau HMI tant que Nextion Editor n'a pas validé la compilation.

## Périmètre validé

- **Écran unique pour cette étape :** Nextion Enhanced `NX4832K035_011`, 3,5″ (appelé parfois 4″), 480 × 320.
- Source de référence existante : [FlowIO_Nextion_NX4832K035_011-6.0.0.HMI (6.0.0)](../6.0.0/FlowIO_Nextion_NX4832K035_011-6.0.0.HMI).
- **HMI 7.0.0 de référence (validé sur écran réel) :** [`FlowIO_Nextion_NX4832K035_011-7.0.0.HMI`](FlowIO_Nextion_NX4832K035_011-7.0.0.HMI) : 480 × 320 uniquement, jauges modernisées, logo officiel, thermomètre de piscine rouge, Wi-Fi coloré et redessin après veille. Version précédente sauvegardée sur la branche indiquée ci-dessus.
- Générateur du nouveau design : [`build_3p5_v7_modern.py`](../../scripts/build_3p5_v7_modern.py) avec [`validate_3p5_v7_modern.py`](../../scripts/validate_3p5_v7_modern.py). Le workflow [`nextion-7-modern.yml`](../../../.github/workflows/nextion-7-modern.yml) reconstruit toujours le HMI depuis la 7.0.0 validée archivée (et non depuis un HMI déjà modifié).
- **Les modèles 5″ et 7″ sont hors périmètre** : aucun HMI/TFT n'est modifié pour eux dans cette étape.
- Conserver tous les noms de variables, IDs d'objets, gestion des pages, codes d'actions et messages série déjà utilisés par le firmware Waveshare.

## Points de contrôle du nouveau design dans Nextion Editor

1. Sur la page Home, réorganiser **seulement le bandeau** : logo flow.io à gauche, date `JJ/MM/AA` et heure `HH:MM` au centre, état Wi-Fi à droite. Vérifier la lisibilité à **480 × 320** et les éventuels recouvrements.
2. Préserver la variable / l'objet `tTime.txt` déjà alimenté par l'ESP ; ne pas le renommer sans modifier simultanément le firmware.
3. L'heure est affichée au format `HH:MM`, **mise à jour au changement de minute** (contrôle au plus une fois par minute, ou immédiatement au réveil / reconnexion). Pas de mise à jour toutes les 10 secondes.
4. La date est affichée `JJ/MM/AA` et ne change qu'à minuit (ainsi qu'à l'initialisation et au réveil) ; conserver la logique RTC existante, ou mettre à jour le protocole ESP/HMI de façon atomique si un nouveau champ global est ajouté.
5. Conserver le fonctionnement normal du Wi-Fi, des mesures et des jauges. **Ne pas abaisser la fréquence de rafraîchissement des jauges à une minute.**
6. Après réveil du Nextion, vérifier le rendu des jauges pH/ORP et restaurer leur représentation graphique si elle disparaît. S'appuyer sur le chemin existant de *FullRefresh* et éviter une nouvelle boucle permanente de redessin.
7. Conserver les événements tactiles, les valeurs `vapHPercent.val`, `vaOrpPercent.val`, `globals.vaStates.val` et le protocole `printh 23 ...`.

## Vérifications avant publication

- Le générateur vérifie le CRC des pages modifiées, les miroirs du répertoire, le checksum du répertoire (`CRC32_T` suivi de `ADEC`) et la signature `ver21234`. Ces vérifications binaires ne remplacent pas Nextion Editor.
- Ouvrir puis compiler **le fichier `FlowIO_Nextion_NX4832K035_011-7.0.0.HMI`** avec Nextion Editor pour **NX4832K035_011** et vérifier que la compilation n'émet aucune erreur.
- Tester l'affichage de la date, de l'heure, du Wi-Fi et des jauges au démarrage puis à la sortie de veille.
- Tester passage de minute, passage de minuit, heure NTP/RTC et reconnexion.
- Confirmer que les commandes tactiles et les événements de la page Home n'ont pas régressé.
- Confirmer les transferts OTA Nextion et la compatibilité modèle avant de renommer le binaire.
- Ouvrir et compiler d'abord le HMI de test ci-dessus ; publier le TFT compilé sous `FlowIO_Nextion_NX4832K035_011-7.0.0.tft` **uniquement après les contrôles**.
- **Ne pas changer** `common.nextion_firmware_version` dans `platformio.ini` : il doit rester à `7.0.0`. Compiler le nouveau HMI pour obtenir un nouveau `.tft` 7.0.0 seulement après validation.

Références : [protocole ESP/Nextion](../../../docs/integration/nextion-esp-protocol.md) · [documentation hardware](../../../docs/hardware/nextion-displays.md).

## Validation historique de la 7.0.0 précédente (Nextion2Text)

Un controle reproductible est lance sur la branche `dev` pour le NX4832K035_011 :

- Workflow : [Validate Nextion 3.5in HMI 7.0.0](../../../.github/workflows/nextion-hmi-validate.yml).
- Script : [compare_3p5_hmi.py](../../scripts/compare_3p5_hmi.py).
- Verification : signature `ver21234`, CRC du repertoire et de ses miroirs, CRC des 9 pages,
  positions/longueurs des composants, et absence de changements dans les autres ressources.
- Nextion2Text (`MMMZZZZ/Nextion2Text`, MPL-2.0) est telecharge et verifie a l'execution,
  sans etre recopie dans ce depot. Il exporte les sources texte/JSON (positions et attributs inclus).
- L'artefact **Nextion-NX4832K035-HMI-7.0.0-VALIDATION** contient
  `VALIDATION.md`, `nextion2text.diff`, `v6/` et `v7/` (conservation 14 jours).
- [Premiere execution validee](https://github.com/stephdust/Flow.io-Waveshare/actions/runs/45971255561) : seuls
  `globals` et `pageHome` diffèrent (fichiers .txt et JSON).

La validation automatique n'est **pas** une preuve de compilation par Nextion Editor.
Elle ne prouve pas non plus la correction du probleme de jauges invisibles apres reveil.
**Attention** : verifier que la source 6.0.0 de GitHub est bien la meme que votre
source locale avant de considerer un fichier 7.0.0 comme finalise.


## Modernisation Home (27 novembre 2026) — modèle 480 × 320 seulement

- Les ressources modifiées sont strictement `pageHome` (19.pa), l'atlas d'images des jauges (36.i) et les cinq images de filtration (4.i, 8.i, 28.i, 29.i, 26.i).
- `globals` (5.pa), le manifeste matériel (`main.HMI`), les autres pages, les identifiants des composants et les références des objets série sont conservés.
- Les chiffres verts de référence pH et ORP sont présentés **sans encadrement** ; nouveau logo Flow.io, pictogramme thermomètre + piscine, interface bleu nuit.
- Validation GitHub : [workflow de génération et contrôle des ressources](https://github.com/stephdust/Flow.io-Waveshare/actions/runs/45987260043), avec CRC des pages et répertoire, version 7.0.0 inchangée et comparaison à la source validée.
- **La validation d'ouverture/compilation dans Nextion Editor et la validation réelle du redessin des jauges sur cette version restent à faire.**
- Ni les projets ni les TFT des **Nextion 5″ ou 7″** ne sont concernés.

## Nouvelle chaîne recommandée (source éditable)

```text
HMI 7.0.0 validé → nxwright extract → modifier pageHome.nx / pageHome.page.toml / PNG
  → nxwright check → nxwright build → nouveau HMI 7.0.0 expérimental
  → nxwright compile --download → TFT NX4832K035 TEST-ONLY
```

Le [workflow d'essai réussi](https://github.com/stephdust/Flow.io-Waveshare/actions/runs/46004942701) conserve les mêmes identifiants de composants et événements série. La génération n'est pas une validation physique ; ouvrir le HMI dans Nextion Editor et vérifier les jauges/veille avant d'autoriser la publication du TFT.
