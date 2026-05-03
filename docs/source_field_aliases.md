# Source Field Aliases

Schema v1.0 uses source field aliases to map API/export fields to canonical columns. Aliases are mapping policy, not source of truth; raw payloads remain preserved.

## Core Mapping Policy

| source field | target |
|---|---|
| `TEST.TSTNO` | `tests.test_no` |
| `TEST.TSTDAT` | `tests.test_date_raw` / `tests.test_date` |
| `TEST.TSTPRFD` | `tests.test_performer` |
| `TEST.TSTCFND` | `tests.test_configuration` |
| `TEST.CLSSPD` | `tests.closing_speed_raw` / `tests.closing_speed` |
| `VEHICLE.VEHNO` / `vehicleNo` | canonical identity context, not dictionary |
| `VEHICLE.MAKED` / `vehicleMake` | `vehicles.make` |
| `VEHICLE.MODELD` / `vehicleModel` | `vehicles.model` |
| `VEHICLE.YEAR` / `modelYear` | `vehicles.model_year`, never scope |
| `VEHICLE.BODYD` | `vehicles.body_type` |
| `VEHICLE.VEHTWT` / `vehicleTestWeight` | `vehicles.vehicle_test_weight_raw` / `vehicles.vehicle_test_weight` |
| `VEHICLE.CURBWT` | `vehicles.curb_weight_raw` / `vehicles.curb_weight` |
| `VEHICLE.VEHLEN` / `vehicleLength` | `vehicles.vehicle_length_raw` / `vehicles.vehicle_length` |
| `VEHICLE.VEHWID` / `vehicleWidth` | `vehicles.vehicle_width_raw` / `vehicles.vehicle_width` |
| `VEHICLE.WHLBAS` | `vehicles.wheelbase_raw` / `vehicles.wheelbase` |
| `VEHICLE.CRHDST` / `vaxCrushDistance` | `vehicles.vax_crush_distance_raw` / `vehicles.vax_crush_distance` |
| `VEHICLE.VEHSPD` / `vehicleSpeed` | `vehicles.vehicle_speed_raw` / `vehicles.vehicle_speed` |
| `BARRIER.BARRIGD` / `rigidOrDeformableBarrier` | `barriers.rigidity` |
| `BARRIER.BARSHPD` / `barrierShape` | `barriers.shape` |
| `BARRIER.BARANG` | `barriers.angle_raw` / `barriers.angle` |
| `OCCUPANT.OCCLOC` / `occupantLocation` | `occupants.occupant_location_raw` / normalized slot |
| `OCCUPANT.OCCTYPD` / `occupantType` | `occupants.occupant_type` |
| `OCCUPANT.HIC` / `headInjuryCriterion` | `injury_metrics(metric_code='HIC')` or numeric backlog |
| `restraintType` | `restraints.restraint_type` |
| `restraintDeployment` | `restraints.deployment_status` |
| `sensorType` | `instrumentation_channels.sensor_type` |
| `sensorAttachment` | `instrumentation_channels.sensor_attachment` |
| `axisDirofSensor` | `instrumentation_channels.sensor_axis` |
| `dataMeasurementUnits` | `instrumentation_channels.unit_raw` |
| `dataStatus` | `instrumentation_channels.data_status` |
| `channelStatus` | `instrumentation_channels.channel_status` |

## Dictionary / code_values Alias Policy

Allowed domain registry fields:

- sensor type, attachment, axis, unit, data status, channel status
- occupant location and occupant type
- restraint type and deployment
- barrier rigidity and shape
- asset kind and subtype
- test configuration key
- classification status
- participant kind

Not dictionary aliases:

- `testNo`, `vehicleNo`, `curveNo`
- row ids, URL/hash/path fields
- numeric measurements and time increments
- file/package internals

## Conflict Policy

Aliases can resolve benign label/code differences. Alias mapping must not hide scope/date conflicts or semantic identity conflicts.
