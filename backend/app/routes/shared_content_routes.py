# app/routes/shared_content_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.database import get_db_async
from app import models
from app.auth_utils import get_current_active_user

router = APIRouter(
    prefix="/shared-content",
    tags=["Shared Content"]
)

# --- Pydantic Schemas ---

class AssignmentQuestionOption(BaseModel):
    text: str
    isCorrect: bool

class AssignmentQuestion(BaseModel):
    text: str
    helperText: Optional[str] = ""
    type: str  # single-choice, multiple-choice, text, etc.
    options: List[AssignmentQuestionOption] = []

class SharedAssignmentCreate(BaseModel):
    training_id: int
    title: str
    description: Optional[str] = ""
    questions: List[AssignmentQuestion]

class SharedAssignmentResponse(BaseModel):
    id: int
    training_id: int
    trainer_username: str
    title: str
    description: Optional[str]
    questions: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FeedbackQuestion(BaseModel):
    text: str
    options: List[str]
    isDefault: bool = False

class SharedFeedbackCreate(BaseModel):
    training_id: int
    defaultQuestions: Optional[List[Dict[str, Any]]] = []
    customQuestions: List[FeedbackQuestion]

class SharedFeedbackResponse(BaseModel):
    id: int
    training_id: int
    trainer_username: str
    defaultQuestions: List[Dict[str, Any]]
    customQuestions: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Routes ---

@router.post("/assignments", response_model=SharedAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def share_assignment(
    assignment_data: SharedAssignmentCreate,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows a trainer to share an assignment for a training they have scheduled.
    """
    trainer_username = current_user.get("username")
    if not trainer_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Verify the training exists
    training_stmt = select(models.TrainingDetail).where(
        models.TrainingDetail.id == assignment_data.training_id
    )
    training_result = await db.execute(training_stmt)
    training = training_result.scalar_one_or_none()
    
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training not found"
        )

    # Verify the current user is the trainer for this training
    # trainer_name can contain multiple trainers separated by newlines
    trainer_name = str(training.trainer_name or "").strip()
    if not trainer_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Training has no trainer assigned"
        )
    
    # Get employee name from ManagerEmployee table for additional matching
    employee_name_result = await db.execute(
        select(models.ManagerEmployee.employee_name).where(
            models.ManagerEmployee.employee_empid == trainer_username
        )
    )
    employee_name = employee_name_result.scalar_one_or_none()
    
    # Normalize strings for comparison
    trainer_name_lower = trainer_name.lower()
    trainer_username_lower = trainer_username.lower()
    employee_name_lower = (employee_name or "").lower()
    
    # Check multiple matching strategies:
    # 1. Exact match with username
    # 2. Exact match with employee name
    # 3. Contains username (for multi-trainer cases)
    # 4. Contains employee name (for multi-trainer cases)
    is_trainer = (
        trainer_name_lower == trainer_username_lower or
        (employee_name_lower and trainer_name_lower == employee_name_lower) or
        trainer_username_lower in trainer_name_lower or
        (employee_name_lower and employee_name_lower in trainer_name_lower)
    )
    
    if not is_trainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only share assignments for trainings you have scheduled"
        )

    # Convert questions to JSON string
    questions_json = json.dumps([q.dict() for q in assignment_data.questions])

    # Check if assignment already exists for this training (update existing)
    existing_stmt = select(models.SharedAssignment).where(
        models.SharedAssignment.training_id == assignment_data.training_id
    )
    existing_result = await db.execute(existing_stmt)
    existing_assignment = existing_result.scalar_one_or_none()

    if existing_assignment:
        # Update existing assignment
        existing_assignment.title = assignment_data.title
        existing_assignment.description = assignment_data.description
        existing_assignment.assignment_data = questions_json
        existing_assignment.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing_assignment)
        
        # Parse and return
        questions_data = json.loads(existing_assignment.assignment_data)
        return SharedAssignmentResponse(
            id=existing_assignment.id,
            training_id=existing_assignment.training_id,
            trainer_username=existing_assignment.trainer_username,
            title=existing_assignment.title,
            description=existing_assignment.description,
            questions=questions_data,
            created_at=existing_assignment.created_at,
            updated_at=existing_assignment.updated_at
        )
    else:
        # Create new assignment
        new_assignment = models.SharedAssignment(
            training_id=assignment_data.training_id,
            trainer_username=trainer_username,
            title=assignment_data.title,
            description=assignment_data.description,
            assignment_data=questions_json
        )
        db.add(new_assignment)
        await db.commit()
        await db.refresh(new_assignment)

        # Parse and return
        questions_data = json.loads(new_assignment.assignment_data)
        return SharedAssignmentResponse(
            id=new_assignment.id,
            training_id=new_assignment.training_id,
            trainer_username=new_assignment.trainer_username,
            title=new_assignment.title,
            description=new_assignment.description,
            questions=questions_data,
            created_at=new_assignment.created_at,
            updated_at=new_assignment.updated_at
        )

@router.post("/feedback", response_model=SharedFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def share_feedback(
    feedback_data: SharedFeedbackCreate,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows a trainer to share feedback form for a training they have scheduled.
    """
    trainer_username = current_user.get("username")
    if not trainer_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Verify the training exists
    training_stmt = select(models.TrainingDetail).where(
        models.TrainingDetail.id == feedback_data.training_id
    )
    training_result = await db.execute(training_stmt)
    training = training_result.scalar_one_or_none()
    
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training not found"
        )

    # Verify the current user is the trainer for this training
    # trainer_name can contain multiple trainers separated by newlines
    trainer_name = str(training.trainer_name or "").strip()
    if not trainer_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Training has no trainer assigned"
        )
    
    # Get employee name from ManagerEmployee table for additional matching
    employee_name_result = await db.execute(
        select(models.ManagerEmployee.employee_name).where(
            models.ManagerEmployee.employee_empid == trainer_username
        )
    )
    employee_name = employee_name_result.scalar_one_or_none()
    
    # Normalize strings for comparison
    trainer_name_lower = trainer_name.lower()
    trainer_username_lower = trainer_username.lower()
    employee_name_lower = (employee_name or "").lower()
    
    # Check multiple matching strategies:
    # 1. Exact match with username
    # 2. Exact match with employee name
    # 3. Contains username (for multi-trainer cases)
    # 4. Contains employee name (for multi-trainer cases)
    is_trainer = (
        trainer_name_lower == trainer_username_lower or
        (employee_name_lower and trainer_name_lower == employee_name_lower) or
        trainer_username_lower in trainer_name_lower or
        (employee_name_lower and employee_name_lower in trainer_name_lower)
    )
    
    if not is_trainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only share feedback for trainings you have scheduled"
        )

    # Convert feedback data to JSON string
    feedback_json = json.dumps({
        "defaultQuestions": feedback_data.defaultQuestions or [],
        "customQuestions": [q.dict() for q in feedback_data.customQuestions]
    })

    # Check if feedback already exists for this training (update existing)
    existing_stmt = select(models.SharedFeedback).where(
        models.SharedFeedback.training_id == feedback_data.training_id
    )
    existing_result = await db.execute(existing_stmt)
    existing_feedback = existing_result.scalar_one_or_none()

    if existing_feedback:
        # Update existing feedback
        existing_feedback.feedback_data = feedback_json
        existing_feedback.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing_feedback)
        
        # Parse and return
        feedback_data_parsed = json.loads(existing_feedback.feedback_data)
        return SharedFeedbackResponse(
            id=existing_feedback.id,
            training_id=existing_feedback.training_id,
            trainer_username=existing_feedback.trainer_username,
            defaultQuestions=feedback_data_parsed.get("defaultQuestions", []),
            customQuestions=feedback_data_parsed.get("customQuestions", []),
            created_at=existing_feedback.created_at,
            updated_at=existing_feedback.updated_at
        )
    else:
        # Create new feedback
        new_feedback = models.SharedFeedback(
            training_id=feedback_data.training_id,
            trainer_username=trainer_username,
            feedback_data=feedback_json
        )
        db.add(new_feedback)
        await db.commit()
        await db.refresh(new_feedback)

        # Parse and return
        feedback_data_parsed = json.loads(new_feedback.feedback_data)
        return SharedFeedbackResponse(
            id=new_feedback.id,
            training_id=new_feedback.training_id,
            trainer_username=new_feedback.trainer_username,
            defaultQuestions=feedback_data_parsed.get("defaultQuestions", []),
            customQuestions=feedback_data_parsed.get("customQuestions", []),
            created_at=new_feedback.created_at,
            updated_at=new_feedback.updated_at
        )

@router.get("/assignments/{training_id}", response_model=Optional[SharedAssignmentResponse])
async def get_shared_assignment(
    training_id: int,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows engineers to retrieve shared assignment for a training assigned to them.
    """
    employee_username = current_user.get("username")
    if not employee_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Verify the training is assigned to this employee
    assignment_stmt = select(models.TrainingAssignment).where(
        models.TrainingAssignment.training_id == training_id,
        models.TrainingAssignment.employee_empid == employee_username
    )
    assignment_result = await db.execute(assignment_stmt)
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access assignments for trainings assigned to you"
        )

    # Get the shared assignment
    assignment_stmt = select(models.SharedAssignment).where(
        models.SharedAssignment.training_id == training_id
    )
    result = await db.execute(assignment_stmt)
    shared_assignment = result.scalar_one_or_none()

    if not shared_assignment:
        return None

    # Parse and return
    questions_data = json.loads(shared_assignment.assignment_data)
    return SharedAssignmentResponse(
        id=shared_assignment.id,
        training_id=shared_assignment.training_id,
        trainer_username=shared_assignment.trainer_username,
        title=shared_assignment.title,
        description=shared_assignment.description,
        questions=questions_data,
        created_at=shared_assignment.created_at,
        updated_at=shared_assignment.updated_at
    )

@router.get("/feedback/{training_id}", response_model=Optional[SharedFeedbackResponse])
async def get_shared_feedback(
    training_id: int,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows engineers to retrieve shared feedback form for a training assigned to them.
    """
    employee_username = current_user.get("username")
    if not employee_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Verify the training is assigned to this employee
    assignment_stmt = select(models.TrainingAssignment).where(
        models.TrainingAssignment.training_id == training_id,
        models.TrainingAssignment.employee_empid == employee_username
    )
    assignment_result = await db.execute(assignment_stmt)
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access feedback for trainings assigned to you"
        )

    # Get the shared feedback
    feedback_stmt = select(models.SharedFeedback).where(
        models.SharedFeedback.training_id == training_id
    )
    result = await db.execute(feedback_stmt)
    shared_feedback = result.scalar_one_or_none()

    if not shared_feedback:
        return None

    # Parse and return
    feedback_data_parsed = json.loads(shared_feedback.feedback_data)
    return SharedFeedbackResponse(
        id=shared_feedback.id,
        training_id=shared_feedback.training_id,
        trainer_username=shared_feedback.trainer_username,
        defaultQuestions=feedback_data_parsed.get("defaultQuestions", []),
        customQuestions=feedback_data_parsed.get("customQuestions", []),
        created_at=shared_feedback.created_at,
        updated_at=shared_feedback.updated_at
    )

@router.get("/trainer/assignments/{training_id}", response_model=Optional[SharedAssignmentResponse])
async def get_shared_assignment_for_trainer(
    training_id: int,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows trainers to check if assignment is already shared for their training.
    """
    trainer_username = current_user.get("username")
    if not trainer_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Verify the training exists
    training_stmt = select(models.TrainingDetail).where(
        models.TrainingDetail.id == training_id
    )
    training_result = await db.execute(training_stmt)
    training = training_result.scalar_one_or_none()
    
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training not found"
        )

    # Verify the current user is a trainer for this training
    trainer_name = str(training.trainer_name or "").strip()
    if not trainer_name:
        return None
    
    # Get employee name for matching
    employee_name_result = await db.execute(
        select(models.ManagerEmployee.employee_name).where(
            models.ManagerEmployee.employee_empid == trainer_username
        )
    )
    employee_name = employee_name_result.scalar_one_or_none()
    
    trainer_name_lower = trainer_name.lower()
    trainer_username_lower = trainer_username.lower()
    employee_name_lower = (employee_name or "").lower()
    
    is_trainer = (
        trainer_name_lower == trainer_username_lower or
        (employee_name_lower and trainer_name_lower == employee_name_lower) or
        trainer_username_lower in trainer_name_lower or
        (employee_name_lower and employee_name_lower in trainer_name_lower)
    )
    
    if not is_trainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check assignments for trainings you have scheduled"
        )

    # Get the shared assignment
    assignment_stmt = select(models.SharedAssignment).where(
        models.SharedAssignment.training_id == training_id
    )
    result = await db.execute(assignment_stmt)
    shared_assignment = result.scalar_one_or_none()

    if not shared_assignment:
        return None

    # Parse and return
    questions_data = json.loads(shared_assignment.assignment_data)
    return SharedAssignmentResponse(
        id=shared_assignment.id,
        training_id=shared_assignment.training_id,
        trainer_username=shared_assignment.trainer_username,
        title=shared_assignment.title,
        description=shared_assignment.description,
        questions=questions_data,
        created_at=shared_assignment.created_at,
        updated_at=shared_assignment.updated_at
    )

@router.get("/trainer/feedback/{training_id}", response_model=Optional[SharedFeedbackResponse])
async def get_shared_feedback_for_trainer(
    training_id: int,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows trainers to check if feedback is already shared for their training.
    """
    trainer_username = current_user.get("username")
    if not trainer_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Verify the training exists
    training_stmt = select(models.TrainingDetail).where(
        models.TrainingDetail.id == training_id
    )
    training_result = await db.execute(training_stmt)
    training = training_result.scalar_one_or_none()
    
    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training not found"
        )

    # Verify the current user is a trainer for this training
    trainer_name = str(training.trainer_name or "").strip()
    if not trainer_name:
        return None
    
    # Get employee name for matching
    employee_name_result = await db.execute(
        select(models.ManagerEmployee.employee_name).where(
            models.ManagerEmployee.employee_empid == trainer_username
        )
    )
    employee_name = employee_name_result.scalar_one_or_none()
    
    trainer_name_lower = trainer_name.lower()
    trainer_username_lower = trainer_username.lower()
    employee_name_lower = (employee_name or "").lower()
    
    is_trainer = (
        trainer_name_lower == trainer_username_lower or
        (employee_name_lower and trainer_name_lower == employee_name_lower) or
        trainer_username_lower in trainer_name_lower or
        (employee_name_lower and employee_name_lower in trainer_name_lower)
    )
    
    if not is_trainer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only check feedback for trainings you have scheduled"
        )

    # Get the shared feedback
    feedback_stmt = select(models.SharedFeedback).where(
        models.SharedFeedback.training_id == training_id
    )
    result = await db.execute(feedback_stmt)
    shared_feedback = result.scalar_one_or_none()

    if not shared_feedback:
        return None

    # Parse and return
    feedback_data_parsed = json.loads(shared_feedback.feedback_data)
    return SharedFeedbackResponse(
        id=shared_feedback.id,
        training_id=shared_feedback.training_id,
        trainer_username=shared_feedback.trainer_username,
        defaultQuestions=feedback_data_parsed.get("defaultQuestions", []),
        customQuestions=feedback_data_parsed.get("customQuestions", []),
        created_at=shared_feedback.created_at,
        updated_at=shared_feedback.updated_at
    )

# --- Assignment Submission Schemas ---

class AnswerSubmission(BaseModel):
    questionIndex: int
    type: str
    selectedOptions: List[int] = []  # For single/multiple choice: indices of selected options
    textAnswer: Optional[str] = ""  # For text-input questions

class AssignmentSubmissionCreate(BaseModel):
    training_id: int
    shared_assignment_id: int
    answers: List[AnswerSubmission]

class QuestionResult(BaseModel):
    questionIndex: int
    isCorrect: bool
    correctAnswers: List[int]  # Indices of correct options
    userAnswers: List[int]  # Indices of user's selected options
    userTextAnswer: Optional[str] = ""  # For text-input questions

class AssignmentResultResponse(BaseModel):
    id: int
    training_id: int
    score: int
    total_questions: int
    correct_answers: int
    question_results: List[QuestionResult]
    submitted_at: datetime

@router.post("/assignments/submit", response_model=AssignmentResultResponse, status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    submission_data: AssignmentSubmissionCreate,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows engineers to submit their answers for an assignment and get evaluated results.
    """
    employee_username = current_user.get("username")
    if not employee_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Verify the training is assigned to this employee
    assignment_stmt = select(models.TrainingAssignment).where(
        models.TrainingAssignment.training_id == submission_data.training_id,
        models.TrainingAssignment.employee_empid == employee_username
    )
    assignment_result = await db.execute(assignment_stmt)
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit assignments for trainings assigned to you"
        )

    # Get the shared assignment
    shared_stmt = select(models.SharedAssignment).where(
        models.SharedAssignment.id == submission_data.shared_assignment_id,
        models.SharedAssignment.training_id == submission_data.training_id
    )
    shared_result = await db.execute(shared_stmt)
    shared_assignment = shared_result.scalar_one_or_none()

    if not shared_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Parse assignment questions
    questions_data = json.loads(shared_assignment.assignment_data)
    total_questions = len(questions_data)
    correct_count = 0
    question_results = []

    # Evaluate answers
    for answer in submission_data.answers:
        if answer.questionIndex >= len(questions_data):
            continue
        
        question = questions_data[answer.questionIndex]
        is_correct = False
        correct_indices = []
        user_indices = answer.selectedOptions.copy()
        
        # Get correct answer indices
        if question.get("type") in ["single-choice", "multiple-choice"]:
            options = question.get("options", [])
            for idx, opt in enumerate(options):
                if opt.get("isCorrect", False):
                    correct_indices.append(idx)
            
            # Check if answer is correct
            if question.get("type") == "single-choice":
                # For single-choice, user should select exactly one option that matches the correct one
                if len(answer.selectedOptions) == 1 and answer.selectedOptions[0] in correct_indices:
                    is_correct = True
            elif question.get("type") == "multiple-choice":
                # For multiple-choice, user's selections must exactly match correct answers
                if set(answer.selectedOptions) == set(correct_indices):
                    is_correct = True
        
        elif question.get("type") == "text-input":
            # For text-input, we'll mark as correct if answer is provided (manual evaluation needed)
            # For now, we'll mark it as needs review
            is_correct = False  # Text answers need manual evaluation
            user_text = answer.textAnswer or ""
        
        if is_correct:
            correct_count += 1
        
        question_results.append({
            "questionIndex": answer.questionIndex,
            "isCorrect": is_correct,
            "correctAnswers": correct_indices,
            "userAnswers": user_indices,
            "userTextAnswer": answer.textAnswer if question.get("type") == "text-input" else None
        })

    # Calculate score (percentage)
    score = int((correct_count / total_questions * 100)) if total_questions > 0 else 0

    # Store submission
    answers_json = json.dumps([a.dict() for a in submission_data.answers])
    submission = models.AssignmentSubmission(
        training_id=submission_data.training_id,
        shared_assignment_id=submission_data.shared_assignment_id,
        employee_empid=employee_username,
        answers_data=answers_json,
        score=score,
        total_questions=total_questions,
        correct_answers=correct_count
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return AssignmentResultResponse(
        id=submission.id,
        training_id=submission.training_id,
        score=submission.score,
        total_questions=submission.total_questions,
        correct_answers=submission.correct_answers,
        question_results=[QuestionResult(**qr) for qr in question_results],
        submitted_at=submission.submitted_at
    )

@router.get("/assignments/{training_id}/result", response_model=Optional[AssignmentResultResponse])
async def get_assignment_result(
    training_id: int,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Allows engineers to retrieve their assignment result for a training.
    """
    employee_username = current_user.get("username")
    if not employee_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Verify the training is assigned to this employee
    assignment_stmt = select(models.TrainingAssignment).where(
        models.TrainingAssignment.training_id == training_id,
        models.TrainingAssignment.employee_empid == employee_username
    )
    assignment_result = await db.execute(assignment_stmt)
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access results for trainings assigned to you"
        )

    # Get the shared assignment
    shared_stmt = select(models.SharedAssignment).where(
        models.SharedAssignment.training_id == training_id
    )
    shared_result = await db.execute(shared_stmt)
    shared_assignment = shared_result.scalar_one_or_none()

    if not shared_assignment:
        return None

    # Get the submission
    submission_stmt = select(models.AssignmentSubmission).where(
        models.AssignmentSubmission.training_id == training_id,
        models.AssignmentSubmission.employee_empid == employee_username,
        models.AssignmentSubmission.shared_assignment_id == shared_assignment.id
    ).order_by(models.AssignmentSubmission.submitted_at.desc())
    submission_result = await db.execute(submission_stmt)
    submission = submission_result.scalar_one_or_none()

    if not submission:
        return None

    # Parse answers and reconstruct question results
    answers_data = json.loads(submission.answers_data)
    questions_data = json.loads(shared_assignment.assignment_data)
    question_results = []

    for answer in answers_data:
        question_idx = answer.get("questionIndex", 0)
        if question_idx >= len(questions_data):
            continue
        
        question = questions_data[question_idx]
        correct_indices = []
        user_indices = answer.get("selectedOptions", [])
        
        # Get correct answer indices
        if question.get("type") in ["single-choice", "multiple-choice"]:
            options = question.get("options", [])
            for idx, opt in enumerate(options):
                if opt.get("isCorrect", False):
                    correct_indices.append(idx)
        
        # Check if answer is correct
        is_correct = False
        if question.get("type") == "single-choice":
            if len(user_indices) == 1 and user_indices[0] in correct_indices:
                is_correct = True
        elif question.get("type") == "multiple-choice":
            if set(user_indices) == set(correct_indices):
                is_correct = True
        
        question_results.append({
            "questionIndex": question_idx,
            "isCorrect": is_correct,
            "correctAnswers": correct_indices,
            "userAnswers": user_indices,
            "userTextAnswer": answer.get("textAnswer") if question.get("type") == "text-input" else None
        })

    return AssignmentResultResponse(
        id=submission.id,
        training_id=submission.training_id,
        score=submission.score,
        total_questions=submission.total_questions,
        correct_answers=submission.correct_answers,
        question_results=[QuestionResult(**qr) for qr in question_results],
        submitted_at=submission.submitted_at
    )

