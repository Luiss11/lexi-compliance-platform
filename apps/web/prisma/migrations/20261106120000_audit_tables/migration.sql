-- audit_logs y evidence_reviews estaban en schema.prisma pero ninguna migración las creaba:
-- en las bases existentes se crearon a mano (audit-tables.sql / prisma db push) y en un
-- servidor nuevo faltaban. IF NOT EXISTS: no hace nada donde ya existen.

CREATE TABLE IF NOT EXISTS "audit_logs" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "actorId" TEXT,
    "action" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT,
    "details" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "audit_logs_tenantId_createdAt_idx" ON "audit_logs"("tenantId", "createdAt");

CREATE TABLE IF NOT EXISTS "evidence_reviews" (
    "id" TEXT NOT NULL,
    "evidenceId" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "verdict" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "issues" JSONB,
    "model" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "evidence_reviews_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "evidence_reviews_evidenceId_idx" ON "evidence_reviews"("evidenceId");
