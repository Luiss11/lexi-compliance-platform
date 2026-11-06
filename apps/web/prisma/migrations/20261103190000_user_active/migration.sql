-- Permite desactivar usuarios sin borrarlos (conserva su nombre en la bitácora y sus tareas).
-- IF NOT EXISTS: es seguro correrla otra vez si la columna ya se creó con "prisma db push".
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "active" BOOLEAN NOT NULL DEFAULT true;
