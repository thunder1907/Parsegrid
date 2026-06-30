from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ExtractedContract(BaseModel):
    """
    Pydantic v2 schema for structured extraction of contract data.
    Every field includes a corresponding confidence score (0.0 to 1.0).
    """
    party_name: Optional[str] = Field(
        default=None, 
        description="The name of the primary counterparty."
    )
    party_name_confidence: float = Field(
        default=1.0, 
        description="Confidence score for party_name (0.0 to 1.0)."
    )
    
    contract_value: Optional[float] = Field(
        default=None, 
        description="The total monetary value of the contract."
    )
    contract_value_confidence: float = Field(
        default=1.0, 
        description="Confidence score for contract_value (0.0 to 1.0)."
    )
    
    payment_terms_days: Optional[int] = Field(
        default=None, 
        description="Payment terms in number of days (e.g., 30 for Net 30)."
    )
    payment_terms_days_confidence: float = Field(
        default=1.0, 
        description="Confidence score for payment_terms_days (0.0 to 1.0)."
    )
    
    penalty_clause_exists: Optional[bool] = Field(
        default=None, 
        description="Whether a penalty clause for late delivery or payment exists."
    )
    penalty_clause_exists_confidence: float = Field(
        default=1.0, 
        description="Confidence score for penalty_clause_exists (0.0 to 1.0)."
    )
    
    governing_law: Optional[str] = Field(
        default=None, 
        description="The governing law or jurisdiction of the contract."
    )
    governing_law_confidence: float = Field(
        default=1.0, 
        description="Confidence score for governing_law (0.0 to 1.0)."
    )
    
    needs_review: bool = Field(
        default=False, 
        description="Flag automatically set to True if any confidence score is less than 0.7."
    )

    @model_validator(mode="after")
    def evaluate_confidence_scores(self) -> "ExtractedContract":
        """
        Validates all confidence fields after model instantiation.
        If any individual confidence score is less than 0.7, sets needs_review to True.
        """
        confidence_scores = [
            self.party_name_confidence,
            self.contract_value_confidence,
            self.payment_terms_days_confidence,
            self.penalty_clause_exists_confidence,
            self.governing_law_confidence,
        ]
        
        if any(score is not None and score < 0.7 for score in confidence_scores):
            self.needs_review = True
            
        return self
