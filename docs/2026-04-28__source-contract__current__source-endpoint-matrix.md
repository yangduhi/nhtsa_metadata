# 2026-04-28 | Source Contract | CURRENT | Source Endpoint Matrix

Base URL: `https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/api/v1`

| name | group | path | paginated | required baseline | allow empty |
|---|---|---|---:|---:|---:|
| test_results | discovery | `/vehicle-database-test-results` | yes | yes | yes |
| search | discovery | `/vehicle-database-test-results/by-search` | no | yes | yes |
| search_vehicle | discovery_optional | `/vehicle-database-test-results/by-search-vehicle` | no | no | yes |
| search_barrier | discovery_optional | `/vehicle-database-test-results/by-search-barrier` | no | no | yes |
| vehicle_models | discovery_optional | `/vehicle-database-test-results/vehicleModels` | no | no | yes |
| occupant_types | discovery_optional | `/vehicle-database-test-results/occupant-types` | no | no | yes |
| test_summary | core | `/vehicle-database-test-results/test-no/{test_no}` | no | yes | yes |
| metadata_export | core | `/vehicle-database-test-results/metadata/{test_no}` | no | yes | yes |
| test_detail | core_optional | `/vehicle-database-test-results/get-test-detail/{test_no}` | no | no | yes |
| vehicle_info | detail | `/vehicle-database-test-results/get-vehicle-info/{test_no}` | no | yes | yes |
| vehicle_detail | detail | `/vehicle-database-test-results/get-vehicle-detail-info/{vehicle_no}/{test_no}` | no | yes | yes |
| barrier_info | detail | `/vehicle-database-test-results/get-barrier-info/{test_no}` | no | yes | yes |
| occupant_info | detail | `/vehicle-database-test-results/get-occupant-info/{test_no}` | no | yes | yes |
| occupant_info_by_vehicle | detail | `/vehicle-database-test-results/get-occupant-info/{vehicle_no}/{test_no}` | no | yes | yes |
| occupant_detail | detail | `/vehicle-database-test-results/get-occupant-detail-information/{vehicle_no}/{test_no}/{occupant_location}` | no | yes | yes |
| restraint_info | detail | `/vehicle-database-test-results/get-restraint-info/{vehicle_no}/{test_no}/{occupant_location}` | no | yes | yes |
| intrusion_info | detail | `/vehicle-database-test-results/get-intrusion-info/{vehicle_no}/{test_no}` | no | yes | yes |
| instrumentation_info | detail | `/vehicle-database-test-results/get-instrumentation-info/{test_no}` | yes | yes | yes |
| instrumentation_detail | detail | `/vehicle-database-test-results/get-instrumentation-detail-info/{curve_no}/{test_no}` | no | yes | yes |
| multimedia_files | assets | `/vehicle-database-test-results/get-multimedia-files/{test_no}` | no | yes | yes |
| vehicle_documents | assets | `/vehicle-documents/test-no/{test_no}` | no | yes | yes |
