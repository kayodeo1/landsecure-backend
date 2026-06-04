"""Seed zones — a faithful port of ``site/assets/js/zones.js``.

Each polygon is a ring of ``[lat, lng]`` pairs (same order as the mockup) so the
ported risk engine reproduces the documented results bit-for-bit.
"""
from __future__ import annotations

GOV_ZONES: list[dict] = [
    {
        "code": "GZ-001",
        "name": "Lekki Free Trade Zone (Acquisition Belt)",
        "zone_type": "Government Acquisition",
        "authority": "Lagos State Government",
        "status": "Restricted",
        "severity": "high",
        "note": "Land compulsorily acquired for the Lekki Free Trade Zone. No private title is recognised within the belt.",
        "legal": "Land Use Act 1978, s.28 (revocation for overriding public interest); Lagos State Gazette No. 17, 2012.",
        "boundary": [[6.3980, 3.6480], [6.4290, 3.6480], [6.4290, 3.7050], [6.3980, 3.7050]],
    },
    {
        "code": "GZ-002",
        "name": "Lagos–Ibadan Expressway Right-of-Way",
        "zone_type": "Infrastructure Corridor",
        "authority": "Federal Ministry of Works",
        "status": "Restricted",
        "severity": "high",
        "note": "Statutory right-of-way reserved along the federal expressway. Setback violations are liable to demolition.",
        "legal": "Highways Act, Cap. H1 LFN 2004; Federal Highways (Declaration) regulations.",
        "boundary": [[6.6250, 3.3650], [6.6700, 3.3650], [6.6700, 3.4050], [6.6250, 3.4050]],
    },
    {
        "code": "GZ-003",
        "name": "Ogun River Floodplain Buffer",
        "zone_type": "Environmental / Protected",
        "authority": "Ogun–Oshun River Basin Authority",
        "status": "Restricted",
        "severity": "high",
        "note": "Statutory 50 m flood buffer along the Ogun River. Building is prohibited within the setback.",
        "legal": "National Environmental (Watershed, Mountainous, Hilly & Catchment Areas) Regulations 2009.",
        "boundary": [[6.7170, 3.3900], [6.7360, 3.3900], [6.7360, 3.4260], [6.7170, 3.4260]],
    },
    {
        "code": "GZ-004",
        "name": "Ibadan Airport Approach Reserve",
        "zone_type": "Aviation Safety Zone",
        "authority": "Federal Airports Authority of Nigeria",
        "status": "Restricted",
        "severity": "high",
        "note": "Obstacle-limitation surface around Ibadan Airport. Height-restricted; new structures require FAAN clearance.",
        "legal": "Civil Aviation Act 2006; Nig. CARs Part 12 (Aerodromes).",
        "boundary": [[7.3370, 3.9650], [7.3560, 3.9650], [7.3560, 3.9890], [7.3370, 3.9890]],
    },
    {
        "code": "GZ-005",
        "name": "University of Ibadan Endowment Land",
        "zone_type": "Government Institution",
        "authority": "University of Ibadan",
        "status": "Restricted",
        "severity": "medium",
        "note": "Land vested in the University. Encroachments are routinely contested and removed.",
        "legal": "University of Ibadan Act, Cap. U7 LFN 2004 (vesting of property).",
        "boundary": [[7.4250, 3.8760], [7.4430, 3.8760], [7.4430, 3.8970], [7.4250, 3.8970]],
    },
    {
        "code": "GZ-006",
        "name": "Asejire Dam Catchment (Protected)",
        "zone_type": "Environmental / Protected",
        "authority": "Oyo State Water Corporation",
        "status": "Restricted",
        "severity": "high",
        "note": "Water-supply catchment for Ibadan. Development is prohibited to protect the reservoir.",
        "legal": "Oyo State Water Corporation Edict; NESREA catchment regulations 2009.",
        "boundary": [[7.3330, 4.1300], [7.3660, 4.1300], [7.3660, 4.1660], [7.3330, 4.1660]],
    },
    {
        "code": "GZ-007",
        "name": "Apapa Port Industrial Reserve",
        "zone_type": "Government Acquisition",
        "authority": "Nigerian Ports Authority",
        "status": "Restricted",
        "severity": "medium",
        "note": "Port-operations land held by the NPA. Private residential title is not granted.",
        "legal": "Nigerian Ports Authority Act, Cap. N126 LFN 2004.",
        "boundary": [[6.4230, 3.3550], [6.4420, 3.3550], [6.4420, 3.3770], [6.4230, 3.3770]],
    },
    {
        "code": "GZ-008",
        "name": "Eleyele Reservoir Setback",
        "zone_type": "Environmental / Protected",
        "authority": "Oyo State Government",
        "status": "Caution",
        "severity": "medium",
        "note": "Buffer around Eleyele reservoir. Partial development controls and pending review apply.",
        "legal": "Oyo State Urban & Regional Planning Law 2010 (development control).",
        "boundary": [[7.4030, 3.8380], [7.4180, 3.8380], [7.4180, 3.8520], [7.4030, 3.8520]],
    },
]

# Verified-clear reference parcels (demo map context only)
SAFE_POINTS: list[dict] = [
    {"name": "Bodija Estate, Ibadan", "lat": 7.4290, "lng": 3.9080},
    {"name": "Magodo GRA, Lagos", "lat": 6.6160, "lng": 3.3750},
]
