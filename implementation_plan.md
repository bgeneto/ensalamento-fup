# Implementation Plan: Enhanced PDF Report with Detailed Scoring Information

## Overview
Enhance the autonomous allocation PDF report to include comprehensive scoring details for each allocated discipline, showing why specific rooms were chosen and the complete scoring breakdown that influenced each allocation decision.

## Types
### New Data Structures
- `DisciplineAllocationDetail`: Contains per-discipline allocation information including scoring breakdown, decision reasoning, and alternative candidates considered
- `ScoringFactorExplanation`: Detailed explanation of each scoring component (hard rules, preferences, historical frequency)

## Files
### Modified Files
- `src/services/autonomous_allocation_report_service.py`: Add new methods for detailed scoring analysis and enhance existing allocation decisions section
- `src/utils/allocation_logger.py`: Ensure all necessary scoring data is captured in decision logging

### New Methods Added
- `_build_detailed_allocation_decisions()`: New section showing per-discipline allocation details with scoring breakdowns
- `_build_scoring_factor_analysis()`: Analysis of which scoring factors influenced each allocation
- `_format_scoring_breakdown_table()`: Helper method to format scoring details in tabular form

## Functions
### New Functions
- `get_detailed_allocation_report(disciplina_codigo=None)`: Enhanced method to get detailed allocation information including scoring breakdowns
- `format_scoring_explanation(scoring_breakdown, allocation_decision)`: Format human-readable scoring explanations

### Modified Functions
- `generate_autonomous_allocation_report()`: Include new detailed sections in the PDF generation flow
- `_build_allocation_decisions()`: Enhanced to include scoring breakdown details

## Classes
### Modified Classes
- `AutonomousAllocationReportService`: Add methods for detailed scoring analysis and decision reasoning

## Dependencies
### No New Dependencies Required
- All enhancements use existing ReportLab PDF generation libraries
- Leverages existing scoring data structures and logging infrastructure

## Testing
### Test Cases
- Verify PDF generation includes new detailed scoring sections
- Test with sample allocation data to ensure scoring breakdowns are correctly displayed
- Validate that decision reasoning explanations are clear and accurate

## Implementation Order
1. ✅ Enhance `AllocationDecisionLogger` to ensure all scoring data is captured
2. ✅ Add new methods to `AutonomousAllocationReportService` for detailed scoring analysis
3. ✅ Modify PDF generation flow to include new detailed sections
4. ✅ Add `scoring_breakdown` field to `AllocationCandidate` dataclass
5. ✅ Update conversion logic to copy scoring data from RoomCandidate to AllocationCandidate
6. ✅ Test PDF generation with sample data - PDF generated successfully (32KB)
7. ✅ Validate scoring explanations and decision reasoning - Implementation complete
