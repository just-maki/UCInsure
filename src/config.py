DATA_URL = "https://www.fema.gov/about/reports-and-data/openfema/v2/FimaNfipClaimsV2.csv"

ALLOWED_COLUMNS = (
    "reportedCity",
    "reportedZipCode",
    "latitude",
    "longitude",
    "floodEvent",
    "dateOfLoss",
    "yearOfLoss",
    "floodZoneCurrent",
    "waterDepth",
    "numberOfFloorsInTheInsuredBuilding",
    "occupancyType",
    "primaryResidenceIndicator",
    "buildingPropertyValue",
    "contentsPropertyValue",
    "amountPaidOnBuildingClaim",
    "amountPaidOnContentsClaim",
    "buildingDamageAmount",
)

TARGET_COLUMN = "riskLevel"

FEATURE_COLUMNS = [
    "reportedCity",
    "reportedZipCode",
    "latitude",
    "longitude",
    "floodEvent",
    "yearOfLoss",
    "floodZoneCurrent",
    "waterDepth",
    "numberOfFloorsInTheInsuredBuilding",
    "occupancyType",
    "primaryResidenceIndicator",
    "buildingPropertyValue",
    "contentsPropertyValue",
    "amountPaidOnBuildingClaim",
    "amountPaidOnContentsClaim",
    "lossMonth",
    "lossDayOfYear",
    "totalClaimAmount",
]

NUMERIC_FEATURES = [
    "latitude",
    "longitude",
    "yearOfLoss",
    "waterDepth",
    "numberOfFloorsInTheInsuredBuilding",
    "buildingPropertyValue",
    "contentsPropertyValue",
    "amountPaidOnBuildingClaim",
    "amountPaidOnContentsClaim",
    "lossMonth",
    "lossDayOfYear",
    "totalClaimAmount",
]

CATEGORICAL_FEATURES = [
    "reportedCity",
    "reportedZipCode",
    "floodEvent",
    "floodZoneCurrent",
    "occupancyType",
    "primaryResidenceIndicator",
]
