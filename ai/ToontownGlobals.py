DonaldsDock = 1000
ToontownCentral = 2000
TheBrrrgh = 3000
MinniesMelodyland = 4000
DaisyGardens = 5000
OutdoorZone = 6000
FunnyFarm = 7000
GoofySpeedway = 8000
DonaldsDreamland = 9000
BarnacleBoulevard = 1100
SeaweedStreet = 1200
LighthouseLane = 1300
SillyStreet = 2100
LoopyLane = 2200
PunchlinePlace = 2300
WalrusWay = 3100
SleetStreet = 3200
PolarPlace = 3300
AltoAvenue = 4100
BaritoneBoulevard = 4200
TenorTerrace = 4300
ElmStreet = 5100
MapleStreet = 5200
OakStreet = 5300
LullabyLane = 9100
PajamaPlace = 9200
ToonHall = 2513
HoodHierarchy = {
    ToontownCentral: (SillyStreet, LoopyLane, PunchlinePlace),
    DonaldsDock: (BarnacleBoulevard, SeaweedStreet, LighthouseLane),
    TheBrrrgh: (WalrusWay, SleetStreet, PolarPlace),
    MinniesMelodyland: (AltoAvenue, BaritoneBoulevard, TenorTerrace),
    DaisyGardens: (ElmStreet, MapleStreet, OakStreet),
    DonaldsDreamland: (LullabyLane, PajamaPlace)
}

WelcomeValleyToken = 0
BossbotHQ = 10000
BossbotLobby = 10100
BossbotCountryClubIntA = 10500
BossbotCountryClubIntB = 10600
BossbotCountryClubIntC = 10700
SellbotHQ = 11000
SellbotLobby = 11100
SellbotFactoryExt = 11200
SellbotFactoryInt = 11500
CashbotHQ = 12000
CashbotLobby = 12100
CashbotMintIntA = 12500
CashbotMintIntB = 12600
CashbotMintIntC = 12700
LawbotHQ = 13000
LawbotLobby = 13100
LawbotOfficeExt = 13200
LawbotOfficeInt = 13300
LawbotStageIntA = 13300
LawbotStageIntB = 13400
LawbotStageIntC = 13500
LawbotStageIntD = 13600
Tutorial = 15000
MyEstate = 16000
GolfZone = 17000
PartyHood = 18000
HoodsAlwaysVisited = [17000, 18000]
WelcomeValleyBegin = 22000
WelcomeValleyEnd = 61000
DynamicZonesBegin = 61000
DynamicZonesEnd = 1 << 20


def isWelcomeValley(zone_id):
    return zone_id == WelcomeValleyToken or WelcomeValleyBegin <= zone_id < WelcomeValleyEnd


def getHoodId(zone_id):
    return zone_id - zone_id % 1000

