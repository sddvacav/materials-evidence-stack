"""Fail-closed TabPFN-v2 admission, model-bank and stacking contracts."""
from .contracts import AdmissionDecision, AdmissionStatus, RuntimeResources, TabPFNRequest, admit_tabpfn
from .model_bank import BankResult, default_factories, group_oof_predictions, train_bank
from .stacking import SimplexStacker, fit_simplex_stacker, project_simplex
__all__=["AdmissionDecision","AdmissionStatus","RuntimeResources","TabPFNRequest","admit_tabpfn","BankResult","default_factories","group_oof_predictions","train_bank","SimplexStacker","fit_simplex_stacker","project_simplex"]
