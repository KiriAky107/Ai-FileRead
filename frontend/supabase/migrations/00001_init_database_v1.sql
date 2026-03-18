-- Create user_role enum
CREATE TYPE public.user_role AS ENUM ('user', 'admin');

-- Create profiles table
CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text,
  phone text,
  role public.user_role DEFAULT 'user'::public.user_role,
  created_at timestamp with time zone DEFAULT now()
);

-- Sync auth.users to profiles trigger
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  user_count int;
BEGIN
  SELECT COUNT(*) INTO user_count FROM profiles;
  INSERT INTO public.profiles (id, email, phone, role)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.phone,
    CASE WHEN user_count = 0 THEN 'admin'::public.user_role ELSE 'user'::public.user_role END
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_confirmed ON auth.users;
CREATE TRIGGER on_auth_user_confirmed
  AFTER UPDATE ON auth.users
  FOR EACH ROW
  WHEN (OLD.confirmed_at IS NULL AND NEW.confirmed_at IS NOT NULL)
  EXECUTE FUNCTION handle_new_user();

-- Create documents table
CREATE TABLE IF NOT EXISTS public.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
  name text NOT NULL,
  type text NOT NULL,
  storage_path text NOT NULL,
  content_text text,
  metadata jsonb DEFAULT '{}'::jsonb,
  status text DEFAULT 'pending',
  created_at timestamp with time zone DEFAULT now()
);

-- Create extracted_entities table
CREATE TABLE IF NOT EXISTS public.extracted_entities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES public.documents(id) ON DELETE CASCADE,
  entity_type text NOT NULL,
  entity_value text NOT NULL,
  confidence float DEFAULT 1.0,
  created_at timestamp with time zone DEFAULT now()
);

-- Create templates table
CREATE TABLE IF NOT EXISTS public.templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
  name text NOT NULL,
  type text NOT NULL,
  storage_path text NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);

-- Create fill_tasks table
CREATE TABLE IF NOT EXISTS public.fill_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
  template_id uuid REFERENCES public.templates(id) ON DELETE CASCADE,
  document_ids uuid[] NOT NULL,
  status text DEFAULT 'pending',
  result_path text,
  error_message text,
  created_at timestamp with time zone DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.extracted_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fill_tasks ENABLE ROW LEVEL SECURITY;

-- Helper function is_admin
CREATE OR REPLACE FUNCTION is_admin(uid uuid)
RETURNS boolean LANGUAGE sql SECURITY DEFINER AS $$
  SELECT EXISTS (
    SELECT 1 FROM profiles p
    WHERE p.id = uid AND p.role = 'admin'::user_role
  );
$$;

-- Policies
-- Profiles: Admin full access, users view/update own (except role)
CREATE POLICY "Admins have full access to profiles" ON profiles
  FOR ALL TO authenticated USING (is_admin(auth.uid()));
CREATE POLICY "Users can view their own profile" ON profiles
  FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY "Users can update their own profile" ON profiles
  FOR UPDATE TO authenticated USING (auth.uid() = id)
  WITH CHECK (role IS NOT DISTINCT FROM (SELECT role FROM profiles WHERE id = auth.uid()));

-- Documents: owner full access, admin view
CREATE POLICY "Users can manage own documents" ON documents
  FOR ALL TO authenticated USING (auth.uid() = owner_id);
CREATE POLICY "Admins can view all documents" ON documents
  FOR SELECT TO authenticated USING (is_admin(auth.uid()));

-- Extracted Entities: owner (via document) full access
CREATE POLICY "Users can manage entities of own docs" ON extracted_entities
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM documents d WHERE d.id = document_id AND d.owner_id = auth.uid())
  );

-- Templates: owner full access
CREATE POLICY "Users can manage own templates" ON templates
  FOR ALL TO authenticated USING (auth.uid() = owner_id);

-- Fill Tasks: owner full access
CREATE POLICY "Users can manage own tasks" ON fill_tasks
  FOR ALL TO authenticated USING (auth.uid() = owner_id);

-- Create storage buckets
INSERT INTO storage.buckets (id, name, public) VALUES ('document_storage', 'document_storage', false) ON CONFLICT (id) DO NOTHING;

-- Storage policies
CREATE POLICY "Users can upload docs" ON storage.objects
  FOR INSERT TO authenticated WITH CHECK (bucket_id = 'document_storage');
CREATE POLICY "Users can view own docs" ON storage.objects
  FOR SELECT TO authenticated USING (bucket_id = 'document_storage' AND (auth.uid()::text = (storage.foldername(name))[1]));
CREATE POLICY "Users can delete own docs" ON storage.objects
  FOR DELETE TO authenticated USING (bucket_id = 'document_storage' AND (auth.uid()::text = (storage.foldername(name))[1]));
