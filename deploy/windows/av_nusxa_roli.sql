-- Agentlar (192.168.100.37 dagi brauzer-sinovchi va tungi zaxira) uchun FAQAT O'QIYDIGAN rol: ishchi bazadan
-- pg_dump bilan nusxa oladi, nusxa o'sha kompyuterda yaratiladi. Bu rol hech narsa yoza olmaydi.
-- Serverda (postgres nomidan), parolni o'zingiz qo'ying:
--   psql -U postgres -d av -v parol="'<KUCHLI_PAROL>'" -f E:\AVPlatform\deploy\windows\av_nusxa_roli.sql

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'av_nusxa') THEN
    CREATE ROLE av_nusxa LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;
ALTER ROLE av_nusxa WITH LOGIN PASSWORD :parol;
ALTER ROLE av_nusxa SET default_transaction_read_only = on;
ALTER ROLE av_nusxa CONNECTION LIMIT 2;

SELECT format('GRANT CONNECT ON DATABASE %I TO av_nusxa', current_database()) \gexec
GRANT USAGE ON SCHEMA public TO av_nusxa;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO av_nusxa;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO av_nusxa;

-- Kelajakdagi jadvallar (yangi migratsiyalar) ham o'qilsin: jadvallar egasi (av) nomidan
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT ON TABLES TO av_nusxa', tableowner)
FROM pg_tables WHERE schemaname = 'public' AND tablename = 'onec_av' \gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT ON SEQUENCES TO av_nusxa', tableowner)
FROM pg_tables WHERE schemaname = 'public' AND tablename = 'onec_av' \gexec
