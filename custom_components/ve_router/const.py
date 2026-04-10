DOMAIN = "ve_router"

CONF_HOST = "host"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ON_PLUG_ACTION = "on_plug_action"
CONF_ON_UNPLUG_ACTION = "on_unplug_action"

DEFAULT_SCAN_INTERVAL = 1
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 60
DEFAULT_ON_PLUG_ACTION = "none"
DEFAULT_ON_UNPLUG_ACTION = "arret"

MANUFACTURER = "GeoSR"
MODEL = "RMS VE"
DEVICE_NAME = "Borne de recharge"

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

PLUG_ACTION_NONE = "none"
PLUG_ACTION_AUTO = "auto"
PLUG_ACTION_SEMI_AUTO = "semi_auto"
PLUG_ACTION_MANUEL = "manuel"
PLUG_ACTION_ARRET = "arret"

PLUG_ACTIONS = {
    PLUG_ACTION_NONE: "Ne rien faire",
    PLUG_ACTION_AUTO: "Passer en mode Auto",
    PLUG_ACTION_SEMI_AUTO: "Passer en mode Semi-auto",
    PLUG_ACTION_MANUEL: "Passer en mode Manuel",
    PLUG_ACTION_ARRET: "Passer en mode Arrêt",
}

PLUG_ACTION_TO_MODE = {
    PLUG_ACTION_AUTO: MODE_AUTO,
    PLUG_ACTION_SEMI_AUTO: MODE_SEMI_AUTO,
    PLUG_ACTION_MANUEL: MODE_MANUEL,
    PLUG_ACTION_ARRET: MODE_ARRET,
}

SERVICE_SET_MODE = "set_mode"
SERVICE_SET_CURRENT = "set_current"

ATTR_ENTRY_ID = "entry_id"
ATTR_MODE = "mode"
ATTR_CURRENT = "current"

CONF_HCHP_ENABLED = "hchp_enabled"
CONF_HCHP_CURRENT = "hchp_current"
CONF_HCHP_ENERGY_WH = "hchp_energy_wh"

DEFAULT_HCHP_ENABLED = False
DEFAULT_HCHP_CURRENT = 10
DEFAULT_HCHP_ENERGY_WH = 0

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "ve_router_"
