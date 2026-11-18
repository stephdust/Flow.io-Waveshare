# Serveur Modbus TCP de Flow.io — configuration et validation

## Configuration Web, MQTT et Home Assistant

Dans la page **Configuration / Config Store**, ouvrir **Network → Modbus TCP**
puis l'un des ports **TCP 502, TCP 503, TCP 504**. La sélection
**Paramètres RS485** remplace l'ancien bouton d'activation :
- **Aucun** : port désactivé, autres champs masqués.
- **Équipement Flow.io** : sélection d'un équipement RS485 configuré ;
  la communication emprunte le séquenceur RS485 commun.
- **Configuration manuelle** : débit, parité et bits d'arrêt spécifiés.

Le timeout et la politique d'erreur restent disponibles pour les ports actifs.
Les données sont désormais des variables **ConfigStore persistantes**, plutôt
que les anciennes structures NVS `mbtcp0/1/2` ; celles-ci sont importées au
premier démarrage si aucune nouvelle valeur n'existe encore. Les paramètres
effectifs du serveur changent **au prochain redémarrage** de Flow.io.

Sur MQTT, Flow.io publie, avec QoS 1 et retained, les paramètres de chaque
port dans les topics usuels :
`<base>/cfg/modbustcp/502`, `<base>/cfg/modbustcp/503` et
`<base>/cfg/modbustcp/504`.

Les **21 entités Home Assistant modifiables** sont enregistrées dans le
service Discovery **existant** (pas un second système). Par port :
- 4 listes de choix : mode RS485, parité, bits d'arrêt, politique d'erreur.
- 3 valeurs numériques : équipement, débit RS485, timeout en ms.

Leurs commandes MQTT utilisent le topic **`<base>/cfg/set`** et les validations
ConfigStore existantes ; la publication d'état confirme la sauvegarde.
Une modification ne redémarre pas automatiquement le contrôleur, afin de
ne pas interrompre le bus RS485 ni les fonctions de sécurité. **Redémarrer
manuellement** pour appliquer une modification aux listeners actifs. Ne pas
confondre l'état configuré publié sur MQTT avec l'état de fonctionnement actif
avant redémarrage.

## Périmètre

Le module `ModbusTcpServerModule` expose trois ports TCP fixes **502, 503 et 504**,
avec **deux connexions entrantes par port** (six au total). Chaque requête valide
est acheminée sans cache par le service `ModbusMasterService`, donc par
`Rs485TransactionScheduler`. Les deux modes d'erreur sont *exception Modbus*
et *silence*. Les paramètres série peuvent venir d'un équipement RS485 Flow.io
ou d'une configuration manuelle par port.

Les tailles désormais autorisées en **Modbus RTU standard** sont FC03/FC04 :
**125 registres** ; FC16 : **123 registres** ; FC06 : un registre. Le protocole
constructeur non standard n'hérite pas automatiquement de ces maxima.

## Test sur matériel (sans écriture)

Après compilation/flashing **du firmware ET du SPIFFS correspondant**, activer
les trois ports dans l'interface et redémarrer si demandé. Choisir pour
chaque port un identifiant TCP, une fonction FC03 ou FC04, et une plage de
registres que l'équipement relié accepte réellement. Ne pas utiliser une
plage arbitraire, surtout sur les appareils utilisant un protocole constructeur
comme AquaGem : la passerelle transmet ici du **Modbus RTU standard**, elle
n'émule pas automatiquement les fonctions propriétaires AquaGem.

Depuis un ordinateur du même réseau :

```sh
python3 scripts/tests/modbus_tcp_load.py --host IP_DE_FLOWIO \
  --target 502:11:52:97:3 \
  --target 503:11:500:24:3 \
  --target 504:11:1000:2:3 \
  --requests 8 --pace-ms 100 --timeout 12 --probe-third
```

**Attention :** les valeurs d'adresse et d'ID ci-dessus ne sont que des
exemples de syntaxe ; les remplacer par des plages autorisées sur **chaque
équipement effectivement associé à chaque port**. La syntaxe d'un `--target`
est `PORT:UNIT_TCP:ADRESSE:NB_REGISTRES:FONCTION`. Une cible par port est
obligatoire. Le client ouvre deux connexions persistantes par port, ne transmet
que des FC03/FC04, vérifie l'en-tête MBAP et la longueur des réponses, et produit
par port : succès, exceptions Modbus, erreurs TCP, moyenne, P50, P95 et maximum
des temps de réponse. `--probe-third` sonde si une troisième connexion par
port est rejetée ; une absence de fermeture dans les deux secondes est
**inconclusive** à cause du backlog TCP et n'est pas une admission confirmée.

Pour tester un bloc de 125 registres, configurer `COUNT=125` **seulement si
le slave expose réellement 125 adresses consécutives**. Une exception Modbus
0x02 (adresse illégale) signifie généralement que l'équipement refuse la
plage, pas que le décodeur TCP limite encore à 32 registres.

## Charge soutenue et indicateurs

Exemple progressif, une fois les lectures courtes stables :

```sh
python3 scripts/tests/modbus_tcp_load.py --host IP_DE_FLOWIO \
  --target 502:11:52:97:3 \
  --target 503:11:500:24:3 \
  --target 504:11:1000:2:3 \
  --requests 100 --pace-ms 200 --timeout 15
```

Pendant l'essai, relever toutes les minutes la ligne série
`[MODBUS-TCP]` : `heap_internal`, `min_internal`,
`largest_internal`, `frag_est_percent`, `psram`,
`largest_psram`, `stack_hwm`, `rtu_queue`, `rtu_peak`,
`rtu_rejected`, `rtu_crc`, `rtu_timeouts`. Les lignes suivantes
détaillent, pour chaque port, les clients actifs, requêtes, réponses,
exceptions, refus, temps TCP maximum, attente en queue maximum et durée RTU
maximum. La route de diagnostic Modbus `GET /api/modbus/ports` est également disponible ; la configuration est maintenant dans Config Store. L'API diagnostique interroge aussi
`GET /api/modbus/ports` (session web authentifiée) et contient des
statistiques par port avec moyenne des temps réseau, de file et de RTU.

Ne pas interpréter une hausse des latences pendant six lectures RS485
simultanées comme une concurrence UART : le bus **reste sérialisé**.
Vérifier surtout qu'il n'y a pas de croissance persistante des allocations,
de perte de réponses, de famine des commandes de sécurité ou de saturation
prolongée de la file. Comparer les mêmes compteurs avant et après l'essai.

La réussite d'un test TCP sur ordinateur ne remplace pas les vérifications sur
matériel des interactions Polytropic/AquaGem, des vitesses série différentes,
du timeout configuré pour chaque port et des fonctions d'écriture FC06/FC16
(à tester à part, avec une procédure sûre et des registres non dangereux).

## Tests hôtes inclus

- `test/host/modbus_tcp_adu.cpp` : MBAP, FC03/FC04 125, FC16 123, dépassement.
- `test/host/modbus_tcp_bridge.cpp` : transfert d'une lecture 125 et écriture 123,
  retour d'exception, délais, écho du Unit ID TCP.
- `test/host/rs485_scheduler.cpp` : codec RTU avec trames maximales, CRC,
  coexistence des propriétaires et priorité sécurité.
- `test/host/modbus_tcp_sessions.cpp` : six sessions, trames partielles,
  admission de deux clients maximum par port.

Le script `scripts/tests/modbus_tcp_load.py` utilise uniquement la bibliothèque
standard de Python 3 ; il ne nécessite ni pymodbus ni Home Assistant.
