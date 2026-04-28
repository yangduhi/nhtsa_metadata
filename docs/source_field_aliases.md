# Source Field Aliases

Initial field mapping policy:

| source field | target |
|---|---|
| `TEST.TSTNO` | `tests.test_no` |
| `TEST.TSTDAT` | `tests.test_date_raw` |
| `TEST.TSTPRFD` | `tests.test_performer` |
| `TEST.TSTCFND` | `tests.test_configuration` |
| `TEST.CLSSPD` | `tests.closing_speed_raw / tests.closing_speed` |
| `VEHICLE.MAKED` | `vehicles.make` |
| `VEHICLE.MODELD` | `vehicles.model` |
| `VEHICLE.YEAR` | `vehicles.model_year` |
| `VEHICLE.VEHSPD` | `vehicles.vehicle_speed_raw / vehicles.vehicle_speed` |
| `BARRIER.BARRIGD` | `barriers.rigidity` |
| `BARRIER.BARSHPD` | `barriers.shape` |
| `BARRIER.BARANG` | `barriers.angle_raw / barriers.angle` |
| `OCCUPANT.OCCLOC` | `occupants.occupant_location_raw` |
| `OCCUPANT.OCCTYPD` | `occupants.occupant_type` |
| `OCCUPANT.HIC` | `injury_metrics(metric_code='HIC')` |
| `API.testNo` | `tests.test_no` |
| `API.testDate` | `tests.test_date_raw` |
| `API.testType` | `tests.test_type` |
| `API.testConfiguration` | `tests.test_configuration` |
| `API.closingSpeed` | `tests.closing_speed` |
| `API.vehicleMake` | `vehicles.make` |
| `API.vehicleModel` | `vehicles.model` |
| `API.modelYear` | `vehicles.model_year` |
| `API.rigidOrDeformableBarrier` | `barriers.rigidity` |
| `API.barrierShape` | `barriers.shape` |
| `API.sensorType` | `instrumentation_channels.sensor_type` |
| `API.axisDirofSensor` | `instrumentation_channels.sensor_axis` |
