from sqlalchemy.orm import Session


class ConflictService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def detect_conflicts_for_test(self, test_no: int) -> int:
        # Phase 5 keeps conflict tracking as a safe stub; source rows remain preserved.
        return 0
