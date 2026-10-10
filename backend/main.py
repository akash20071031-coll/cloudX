from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, SessionLocal
from models import Evidence
from custody import CustodyEvent
from audit import AuditLog
from evidence_service import calculate_sha256, generate_evidence_id
from correlation import correlate_evidence
from report_service import generate_forensic_report

import os
import shutil


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="SecureX - Unified Digital Evidence Platform",
    description=(
        "Secure digital evidence ingestion, integrity verification, "
        "tamper detection, chain of custody, audit logging and "
        "cross-evidence correlation."
    ),
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STORAGE
# ============================================================

EVIDENCE_FOLDER = "../evidence_store"

os.makedirs(EVIDENCE_FOLDER, exist_ok=True)


# ============================================================
# AUDIT LOG HELPER
# ============================================================

def create_audit_log(
    db,
    evidence_id,
    user,
    action,
    details=""
):
    log = AuditLog(
        evidence_id=evidence_id,
        user=user,
        action=action,
        details=details
    )

    db.add(log)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "project": "SecureX",
        "platform": "Unified Digital Evidence Platform",
        "status": "running"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SecureX Backend"
    }


# ============================================================
# 1. EVIDENCE INGESTION
# ============================================================

@app.post("/api/ingest")
def ingest_evidence(
    file: UploadFile = File(...)
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # Validate filename
        # ----------------------------------------------------

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename"
            )

        # Prevent path traversal
        safe_filename = os.path.basename(file.filename)

        if safe_filename in ["", ".", ".."]:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename"
            )

        # ----------------------------------------------------
        # Generate Evidence ID
        # ----------------------------------------------------

        evidence_id = generate_evidence_id()

        # ----------------------------------------------------
        # Create storage path
        # ----------------------------------------------------

        file_path = os.path.join(
            EVIDENCE_FOLDER,
            f"{evidence_id}_{safe_filename}"
        )

        # ----------------------------------------------------
        # Save uploaded file
        # ----------------------------------------------------

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        # ----------------------------------------------------
        # Calculate SHA-256
        # ----------------------------------------------------

        file_hash = calculate_sha256(
            file_path
        )

        # ----------------------------------------------------
        # Create database record
        # ----------------------------------------------------

        evidence = Evidence(
            evidence_id=evidence_id,
            filename=safe_filename,
            file_path=file_path,
            sha256_hash=file_hash,
            status="VERIFIED",
            uploaded_by="Investigator"
        )

        db.add(evidence)

        # ----------------------------------------------------
        # Create audit log
        # ----------------------------------------------------

        create_audit_log(
            db,
            evidence_id,
            "Investigator",
            "EVIDENCE_UPLOADED",
            f"Evidence {safe_filename} uploaded and SHA-256 hash generated"
        )

        # ----------------------------------------------------
        # Commit database changes
        # ----------------------------------------------------

        db.commit()

        return {
            "success": True,
            "evidence_id": evidence_id,
            "filename": safe_filename,
            "sha256": file_hash,
            "status": "VERIFIED",
            "message": "Evidence securely ingested"
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Evidence ingestion failed: {str(e)}"
        )

    finally:
        db.close()


# ============================================================
# 2. LIST ALL EVIDENCE / ARTEFACTS
# ============================================================

@app.get("/api/artefacts")
def get_all_evidence():

    db = SessionLocal()

    try:

        evidence_list = db.query(Evidence).order_by(
            Evidence.uploaded_at.desc()
        ).all()

        return {
            "count": len(evidence_list),

            "artefacts": [
                {
                    "id": evidence.id,
                    "evidence_id": evidence.evidence_id,
                    "filename": evidence.filename,
                    "sha256": evidence.sha256_hash,
                    "status": evidence.status,
                    "uploaded_by": evidence.uploaded_by,
                    "uploaded_at": evidence.uploaded_at
                }

                for evidence in evidence_list
            ]
        }

    finally:
        db.close()


# ============================================================
# 3. VERIFY EVIDENCE INTEGRITY
# ============================================================

@app.get("/api/verify/{evidence_id}")
def verify_evidence(
    evidence_id: str
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # Find evidence
        # ----------------------------------------------------

        evidence = db.query(Evidence).filter(
            Evidence.evidence_id == evidence_id
        ).first()

        if not evidence:
            raise HTTPException(
                status_code=404,
                detail="Evidence not found"
            )

        # ----------------------------------------------------
        # Check whether file exists
        # ----------------------------------------------------

        if not os.path.exists(
            evidence.file_path
        ):

            evidence.status = "MISSING"

            create_audit_log(
                db,
                evidence_id,
                "System",
                "EVIDENCE_MISSING",
                "Stored evidence file could not be found"
            )

            db.commit()

            return {
                "evidence_id": evidence_id,
                "status": "MISSING",
                "message": "Evidence file is missing"
            }

        # ----------------------------------------------------
        # Calculate current SHA-256
        # ----------------------------------------------------

        current_hash = calculate_sha256(
            evidence.file_path
        )

        original_hash = evidence.sha256_hash

        # ----------------------------------------------------
        # Compare hashes
        # ----------------------------------------------------

        if current_hash == original_hash:

            evidence.status = "VERIFIED"

            create_audit_log(
                db,
                evidence_id,
                "System",
                "EVIDENCE_VERIFIED",
                "SHA-256 integrity verification successful"
            )

            db.commit()

            return {
                "evidence_id": evidence_id,
                "status": "VERIFIED",
                "original_sha256": original_hash,
                "current_sha256": current_hash,
                "message": "Evidence integrity verified successfully"
            }

        else:

            evidence.status = "TAMPERED"

            create_audit_log(
                db,
                evidence_id,
                "System",
                "TAMPER_DETECTED",
                "SHA-256 hash mismatch detected"
            )

            db.commit()

            return {
                "evidence_id": evidence_id,
                "status": "TAMPERED",
                "original_sha256": original_hash,
                "current_sha256": current_hash,
                "message": "Possible evidence modification detected"
            }

    finally:
        db.close()


# ============================================================
# 4. TRANSFER CHAIN OF CUSTODY
# ============================================================

@app.post("/api/custody/transfer/{evidence_id}")
def transfer_custody(
    evidence_id: str,
    from_user: str,
    to_user: str,
    notes: str = ""
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # Check evidence exists
        # ----------------------------------------------------

        evidence = db.query(Evidence).filter(
            Evidence.evidence_id == evidence_id
        ).first()

        if not evidence:
            raise HTTPException(
                status_code=404,
                detail="Evidence not found"
            )

        # ----------------------------------------------------
        # Create custody event
        # ----------------------------------------------------

        custody_event = CustodyEvent(
            evidence_id=evidence_id,
            from_user=from_user,
            to_user=to_user,
            action="TRANSFERRED",
            notes=notes
        )

        db.add(custody_event)

        # ----------------------------------------------------
        # Create audit log
        # ----------------------------------------------------

        create_audit_log(
            db,
            evidence_id,
            from_user,
            "CUSTODY_TRANSFERRED",
            (
                f"Evidence transferred from "
                f"{from_user} to {to_user}. "
                f"Notes: {notes}"
            )
        )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        db.commit()

        return {
            "success": True,
            "evidence_id": evidence_id,
            "from_user": from_user,
            "to_user": to_user,
            "action": "TRANSFERRED",
            "notes": notes,
            "message": "Chain of custody updated successfully"
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Custody transfer failed: {str(e)}"
        )

    finally:
        db.close()


# ============================================================
# 5. GET CHAIN OF CUSTODY
# ============================================================

@app.get("/api/custody/{evidence_id}")
def get_custody_history(
    evidence_id: str
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # Check evidence exists
        # ----------------------------------------------------

        evidence = db.query(Evidence).filter(
            Evidence.evidence_id == evidence_id
        ).first()

        if not evidence:
            raise HTTPException(
                status_code=404,
                detail="Evidence not found"
            )

        # ----------------------------------------------------
        # Get custody events
        # ----------------------------------------------------

        events = db.query(CustodyEvent).filter(
            CustodyEvent.evidence_id == evidence_id
        ).order_by(
            CustodyEvent.timestamp.asc()
        ).all()

        return {
            "evidence_id": evidence_id,
            "count": len(events),

            "custody_history": [
                {
                    "id": event.id,
                    "from_user": event.from_user,
                    "to_user": event.to_user,
                    "action": event.action,
                    "notes": event.notes,
                    "timestamp": event.timestamp
                }

                for event in events
            ]
        }

    finally:
        db.close()


# ============================================================
# 6. GET AUDIT LOGS
# ============================================================

@app.get("/api/audit/{evidence_id}")
def get_audit_logs(
    evidence_id: str
):

    db = SessionLocal()

    try:

        logs = db.query(AuditLog).filter(
            AuditLog.evidence_id == evidence_id
        ).order_by(
            AuditLog.timestamp.asc()
        ).all()

        return {
            "evidence_id": evidence_id,
            "count": len(logs),

            "audit_logs": [
                {
                    "id": log.id,
                    "user": log.user,
                    "action": log.action,
                    "details": log.details,
                    "timestamp": log.timestamp
                }

                for log in logs
            ]
        }

    finally:
        db.close()


# ============================================================
# 7. CROSS-EVIDENCE CORRELATION
# ============================================================

@app.get("/api/correlate")
def correlate_all_evidence():

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # Get all evidence
        # ----------------------------------------------------

        evidence_list = db.query(Evidence).order_by(
            Evidence.uploaded_at.asc()
        ).all()

        # ----------------------------------------------------
        # Correlate evidence
        # ----------------------------------------------------

        timeline = correlate_evidence(
            evidence_list
        )

        # ----------------------------------------------------
        # Return unified timeline
        # ----------------------------------------------------

        return {
            "success": True,
            "count": len(timeline),
            "timeline": timeline
        }

    finally:
        db.close()
        # ============================================================
# 8. FORENSIC REPORT GENERATION
# ============================================================

@app.get("/api/report")
def generate_report():

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # Get evidence
        # ----------------------------------------------------

        evidence_list = db.query(Evidence).order_by(
            Evidence.uploaded_at.asc()
        ).all()

        # ----------------------------------------------------
        # Get custody events
        # ----------------------------------------------------

        custody_events = db.query(
            CustodyEvent
        ).order_by(
            CustodyEvent.timestamp.asc()
        ).all()

        # ----------------------------------------------------
        # Get audit logs
        # ----------------------------------------------------

        audit_logs = db.query(
            AuditLog
        ).order_by(
            AuditLog.timestamp.asc()
        ).all()

        # ----------------------------------------------------
        # Create correlation timeline
        # ----------------------------------------------------

        correlation_timeline = correlate_evidence(
            evidence_list
        )

        # ----------------------------------------------------
        # Generate report
        # ----------------------------------------------------

        report_path, filename = generate_forensic_report(
            evidence_list,
            custody_events,
            audit_logs,
            correlation_timeline
        )

        return {
            "success": True,
            "filename": filename,
            "report_path": report_path,
            "evidence_count": len(evidence_list),
            "custody_event_count": len(custody_events),
            "audit_log_count": len(audit_logs),
            "correlation_event_count": len(
                correlation_timeline
            ),
            "message": "Forensic report generated successfully"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(e)}"
        )

    finally:
        db.close()