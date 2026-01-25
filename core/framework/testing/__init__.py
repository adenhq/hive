# Heavy dependencies lazy loaded or imported directly to keep CLI fast
# from .test_case import TestCase, TestSuite
# from .test_result import TestResult 
# from .test_storage import TestStorage
from .failure_record import FailureRecord, FailureSeverity
from .failure_storage import FailureStorage
