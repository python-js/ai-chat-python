-- AlterTable
ALTER TABLE "Document" ADD COLUMN "lastProgressAt" TIMESTAMP(3),
ADD COLUMN "retryCount" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN "lastError" TEXT;
