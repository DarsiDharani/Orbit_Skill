"""
Assignment Routes Module

Purpose: API routes for training assignment management
Features:
- Assign trainings to employees (managers only)
- Get assignments for current user
- Get team assignments (managers only)
- Delete assignments

Endpoints:
- POST /assignments/: Assign training to employee
- GET /assignments/my: Get current user's assignments
- GET /assignments/manager/team: Get team assignments (manager only)
- DELETE /assignments/{id}: Delete assignment

@author Orbit Skill Development Team
@date 2025
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy import delete

from app.database import get_db_async
from app import models
from app.auth_utils import get_current_active_user # Using your auth dependency

router = APIRouter(
    prefix="/assignments",
    tags=["Assignments"]
)

class AssignmentCreate(BaseModel):
    """Request schema for creating a training assignment"""
    training_id: int
    employee_username: str

@router.post("/", status_code=201)
async def assign_training_to_employee(
    assignment: AssignmentCreate,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user) # Get the logged-in manager
):
    """
    Creates an assignment record linking a training to an employee.
    Called by the manager's dashboard.
    """
    manager_username = current_user.get("username")

    # Check if assignment already exists
    existing_assignment_stmt = select(models.TrainingAssignment).where(
        models.TrainingAssignment.training_id == assignment.training_id,
        models.TrainingAssignment.employee_empid == assignment.employee_username
    )
    existing_assignment_result = await db.execute(existing_assignment_stmt)
    if existing_assignment_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, 
            detail="This training is already assigned to this employee"
        )

    # Create the new assignment record
    db_assignment = models.TrainingAssignment(
        training_id=assignment.training_id,
        employee_empid=assignment.employee_username,
        manager_empid=manager_username
    )
    db.add(db_assignment)
    await db.commit()
    await db.refresh(db_assignment)
    
    return {"message": "Training assigned successfully"}

@router.get("/my")
async def get_my_assigned_trainings(
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Returns training details for trainings assigned to the current logged-in user (employee).
    """
    employee_username = current_user.get("username")

    # Join assignments with training details
    stmt = select(models.TrainingDetail).join(
        models.TrainingAssignment,
        models.TrainingAssignment.training_id == models.TrainingDetail.id
    ).where(models.TrainingAssignment.employee_empid == employee_username)

    result = await db.execute(stmt)
    trainings = result.scalars().all()

    # Serialize minimal fields
    def to_iso(val):
        if isinstance(val, (date, datetime)):
            return val.isoformat()
        if isinstance(val, str):
            try:
                # Try parse ISO-like strings
                return datetime.fromisoformat(val).date().isoformat()
            except Exception:
                return val
        return None

    def serialize(td: models.TrainingDetail):
        return {
            "id": td.id,
            "division": td.division,
            "department": td.department,
            "competency": td.competency,
            "skill": td.skill,
            "training_name": td.training_name,
            "training_topics": td.training_topics,
            "prerequisites": td.prerequisites,
            "skill_category": td.skill_category,
            "trainer_name": td.trainer_name,
            "email": td.email,
            "training_date": to_iso(td.training_date),
            "duration": td.duration,
            "time": td.time,
            "training_type": td.training_type,
            "seats": td.seats,
            "assessment_details": td.assessment_details,
        }

    return [serialize(t) for t in trainings]

@router.get("/manager/team")
async def get_team_assigned_trainings(
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Returns all training assignments for the manager's team members.
    Returns a list of assignments with training_id and employee_empid for duplicate checking.
    """
    manager_username = current_user.get("username")
    
    # Get all team member IDs for this manager
    team_members_stmt = select(models.ManagerEmployee.employee_empid).where(
        models.ManagerEmployee.manager_empid == manager_username
    )
    team_result = await db.execute(team_members_stmt)
    team_member_ids = [row[0] for row in team_result.all()]
    
    if not team_member_ids:
        return []
    
    # Get all assignments for team members managed by this manager
    assignments_stmt = select(models.TrainingAssignment).where(
        models.TrainingAssignment.employee_empid.in_(team_member_ids),
        models.TrainingAssignment.manager_empid == manager_username
    )
    assignments_result = await db.execute(assignments_stmt)
    assignments = assignments_result.scalars().all()
    
    # Return simple structure for duplicate checking
    return [
        {
            "training_id": assignment.training_id,
            "employee_empid": assignment.employee_empid
        }
        for assignment in assignments
    ]

@router.delete("/{training_id}/{employee_empid}", status_code=200)
async def delete_assignment(
    training_id: int,
    employee_empid: str,
    db: AsyncSession = Depends(get_db_async),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Deletes an assignment record. Used when manager wants to reassign a training.
    Only the manager who assigned the training can delete it.
    """
    manager_username = current_user.get("username")
    if not manager_username:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )
    
    # Find the assignment
    assignment_stmt = select(models.TrainingAssignment).where(
        models.TrainingAssignment.training_id == training_id,
        models.TrainingAssignment.employee_empid == employee_empid,
        models.TrainingAssignment.manager_empid == manager_username
    )
    assignment_result = await db.execute(assignment_stmt)
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found or you are not authorized to delete it"
        )
    
    # Delete the assignment
    delete_stmt = delete(models.TrainingAssignment).where(
        models.TrainingAssignment.training_id == training_id,
        models.TrainingAssignment.employee_empid == employee_empid,
        models.TrainingAssignment.manager_empid == manager_username
    )
    await db.execute(delete_stmt)
    await db.commit()
    
    return {"message": "Assignment deleted successfully"}