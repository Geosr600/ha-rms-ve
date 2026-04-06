DOMAIN = "ve_router"

CONF_HOST = "host"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 1
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 60

MANUFACTURER = "GeoSR"
MODEL = "RMS VE"
DEVICE_NAME = "Borne de recharge"  # titre par défaut de la carte

MODE_AUTO = 0
MODE_SEMI_AUTO = 1
MODE_MANUEL = 2
MODE_ARRET = 3

MODE_LABELS = {
    MODE_AUTO: "Auto",
    MODE_SEMI_AUTO: "Semi-auto",
    MODE_MANUEL: "Manuel",
    MODE_ARRET: "Arrêt",
}

MODE_BY_LABEL = {value: key for key, value in MODE_LABELS.items()}
