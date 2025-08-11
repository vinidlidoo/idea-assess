"""
Agent Interface Definitions for Business Idea Evaluator

This module defines the abstract interfaces and data structures
for the four specialized agents in the evaluation pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


# Data Structures

class Grade(Enum):
    """Letter grades for evaluation criteria"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass
class IdeaInput:
    """Input structure for new business ideas"""
    idea: str
    slug: str  # Generated from idea text
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AnalysisDocument:
    """Output from Analyst and Reviewer agents"""
    idea_slug: str
    content: str  # Markdown formatted
    sections: Dict[str, str]  # Section name -> content
    word_count: int
    research_sources: List[str]
    timestamp: datetime
    version: int  # Incremented by Reviewer


@dataclass
class EvaluationCriterion:
    """Single evaluation criterion with grade and justification"""
    name: str
    grade: Grade
    score: float  # 0.0 to 1.0 for averaging
    justification: str
    evidence: List[str]  # Specific points from analysis


@dataclass
class EvaluationResult:
    """Output from Judge agent"""
    idea_slug: str
    overall_grade: Grade
    criteria: List[EvaluationCriterion]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    timestamp: datetime


@dataclass
class ComparativeReport:
    """Output from Synthesizer agent"""
    ideas_analyzed: List[str]
    rankings: List[Dict[str, Any]]  # Ordered by overall grade
    executive_summary: str
    comparison_table: str  # Markdown table
    top_opportunities: List[str]
    patterns_identified: List[str]
    timestamp: datetime


# Agent Interfaces

class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.system_prompt = self._load_system_prompt()
    
    @abstractmethod
    def _load_system_prompt(self) -> str:
        """Load agent-specific system prompt"""
        pass
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Main processing method for the agent"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data before processing"""
        pass
    
    @abstractmethod
    def validate_output(self, output_data: Any) -> bool:
        """Validate output data after processing"""
        pass
    
    async def process_with_validation(self, input_data: Any) -> Any:
        """Process with input/output validation"""
        if not self.validate_input(input_data):
            raise ValueError(f"Invalid input for {self.name}")
        
        output = await self.process(input_data)
        
        if not self.validate_output(output):
            raise ValueError(f"Invalid output from {self.name}")
        
        return output


class IAnalystAgent(BaseAgent):
    """Interface for the Analyst agent"""
    
    @abstractmethod
    async def research_market(self, idea: str) -> Dict[str, Any]:
        """Conduct market research for the idea"""
        pass
    
    @abstractmethod
    async def analyze_competitors(self, idea: str) -> List[Dict[str, Any]]:
        """Analyze competitive landscape"""
        pass
    
    @abstractmethod
    async def assess_feasibility(self, idea: str) -> Dict[str, Any]:
        """Assess technical and business feasibility"""
        pass
    
    @abstractmethod
    async def generate_analysis(self, 
                              idea: IdeaInput,
                              research_data: Dict[str, Any]) -> AnalysisDocument:
        """Generate comprehensive analysis document"""
        pass
    
    async def process(self, input_data: IdeaInput) -> AnalysisDocument:
        """Transform one-liner idea into full analysis"""
        # Orchestrate research and analysis generation
        market_data = await self.research_market(input_data.idea)
        competitors = await self.analyze_competitors(input_data.idea)
        feasibility = await self.assess_feasibility(input_data.idea)
        
        research_data = {
            "market": market_data,
            "competitors": competitors,
            "feasibility": feasibility
        }
        
        return await self.generate_analysis(input_data, research_data)


class IReviewerAgent(BaseAgent):
    """Interface for the Reviewer agent"""
    
    @abstractmethod
    async def identify_gaps(self, analysis: AnalysisDocument) -> List[str]:
        """Identify gaps and weaknesses in analysis"""
        pass
    
    @abstractmethod
    async def fact_check(self, analysis: AnalysisDocument) -> List[Dict[str, Any]]:
        """Verify claims and data points"""
        pass
    
    @abstractmethod
    async def enhance_narrative(self, analysis: AnalysisDocument) -> str:
        """Improve narrative flow and clarity"""
        pass
    
    @abstractmethod
    async def add_missing_sections(self, 
                                  analysis: AnalysisDocument,
                                  gaps: List[str]) -> Dict[str, str]:
        """Add content for identified gaps"""
        pass
    
    async def process(self, input_data: AnalysisDocument) -> AnalysisDocument:
        """Review and enhance analysis document"""
        gaps = await self.identify_gaps(input_data)
        fact_checks = await self.fact_check(input_data)
        enhanced_content = await self.enhance_narrative(input_data)
        
        if gaps:
            new_sections = await self.add_missing_sections(input_data, gaps)
            # Merge new sections into analysis
            input_data.sections.update(new_sections)
        
        # Create enhanced version
        enhanced = AnalysisDocument(
            idea_slug=input_data.idea_slug,
            content=enhanced_content,
            sections=input_data.sections,
            word_count=len(enhanced_content.split()),
            research_sources=input_data.research_sources,
            timestamp=datetime.now(),
            version=input_data.version + 1
        )
        
        return enhanced


class IJudgeAgent(BaseAgent):
    """Interface for the Judge agent"""
    
    EVALUATION_CRITERIA = [
        "Market Opportunity",
        "Technical Feasibility",
        "Competitive Advantage",
        "Revenue Potential",
        "Risk Assessment",
        "Team/Resource Requirements",
        "Innovation Level"
    ]
    
    @abstractmethod
    async def evaluate_criterion(self, 
                                analysis: AnalysisDocument,
                                criterion: str) -> EvaluationCriterion:
        """Evaluate a single criterion"""
        pass
    
    @abstractmethod
    async def calculate_overall_grade(self, 
                                     criteria: List[EvaluationCriterion]) -> Grade:
        """Calculate overall grade from individual criteria"""
        pass
    
    @abstractmethod
    async def generate_recommendations(self, 
                                      analysis: AnalysisDocument,
                                      criteria: List[EvaluationCriterion]) -> List[str]:
        """Generate actionable recommendations"""
        pass
    
    async def process(self, input_data: AnalysisDocument) -> EvaluationResult:
        """Evaluate analysis against fixed criteria"""
        criteria_results = []
        
        for criterion_name in self.EVALUATION_CRITERIA:
            result = await self.evaluate_criterion(input_data, criterion_name)
            criteria_results.append(result)
        
        overall_grade = await self.calculate_overall_grade(criteria_results)
        recommendations = await self.generate_recommendations(input_data, criteria_results)
        
        # Extract strengths and weaknesses
        strengths = [c.justification for c in criteria_results if c.grade in [Grade.A, Grade.B]]
        weaknesses = [c.justification for c in criteria_results if c.grade in [Grade.C, Grade.D]]
        
        return EvaluationResult(
            idea_slug=input_data.idea_slug,
            overall_grade=overall_grade,
            criteria=criteria_results,
            strengths=strengths[:5],  # Top 5
            weaknesses=weaknesses[:5],  # Top 5
            recommendations=recommendations,
            timestamp=datetime.now()
        )


class ISynthesizerAgent(BaseAgent):
    """Interface for the Synthesizer agent"""
    
    @abstractmethod
    async def rank_ideas(self, 
                        evaluations: List[EvaluationResult]) -> List[Dict[str, Any]]:
        """Rank ideas by overall grade and criteria"""
        pass
    
    @abstractmethod
    async def identify_patterns(self, 
                               evaluations: List[EvaluationResult]) -> List[str]:
        """Identify patterns across evaluations"""
        pass
    
    @abstractmethod
    async def generate_comparison_table(self, 
                                       evaluations: List[EvaluationResult]) -> str:
        """Generate markdown comparison table"""
        pass
    
    @abstractmethod
    async def write_executive_summary(self, 
                                     rankings: List[Dict[str, Any]],
                                     patterns: List[str]) -> str:
        """Write executive summary of findings"""
        pass
    
    async def process(self, 
                     input_data: List[EvaluationResult]) -> ComparativeReport:
        """Generate comparative report across multiple evaluations"""
        rankings = await self.rank_ideas(input_data)
        patterns = await self.identify_patterns(input_data)
        comparison_table = await self.generate_comparison_table(input_data)
        executive_summary = await self.write_executive_summary(rankings, patterns)
        
        # Get top opportunities (top 3 ranked ideas)
        top_opportunities = [r["idea_slug"] for r in rankings[:3]]
        
        return ComparativeReport(
            ideas_analyzed=[e.idea_slug for e in input_data],
            rankings=rankings,
            executive_summary=executive_summary,
            comparison_table=comparison_table,
            top_opportunities=top_opportunities,
            patterns_identified=patterns,
            timestamp=datetime.now()
        )


# Pipeline Interface

class IPipeline(ABC):
    """Interface for the evaluation pipeline"""
    
    @abstractmethod
    async def evaluate_idea(self, idea: str) -> Dict[str, Any]:
        """Evaluate a single business idea"""
        pass
    
    @abstractmethod
    async def evaluate_batch(self, ideas: List[str]) -> ComparativeReport:
        """Evaluate multiple ideas and generate comparative report"""
        pass
    
    @abstractmethod
    async def resume_from_checkpoint(self, idea_slug: str) -> Dict[str, Any]:
        """Resume evaluation from last checkpoint"""
        pass
    
    @abstractmethod
    def save_checkpoint(self, stage: str, data: Any) -> None:
        """Save checkpoint for recovery"""
        pass