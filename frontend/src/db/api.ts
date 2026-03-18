import { supabase } from './supabase';
import type { Document, ExtractedEntity, Template, FillTask } from '../types/types';

export const documentApi = {
  async listDocuments(userId: string) {
    const { data, error } = await supabase
      .from('documents')
      .select('*, extracted_entities(*)')
      .eq('owner_id', userId)
      .order('created_at', { ascending: false });
    
    if (error) throw error;
    return data;
  },

  async uploadDocument(file: File, userId: string) {
    const fileExt = file.name.split('.').pop();
    const fileName = `${userId}/${Math.random().toString(36).substring(2, 15)}.${fileExt}`;
    const filePath = `documents/${fileName}`;

    const { error: uploadError } = await supabase.storage
      .from('document_storage')
      .upload(filePath, file);

    if (uploadError) throw uploadError;

    const { data, error } = await supabase
      .from('documents')
      .insert({
        owner_id: userId,
        name: file.name,
        type: fileExt || 'unknown',
        storage_path: filePath,
        status: 'pending'
      })
      .select()
      .maybeSingle();

    if (error) throw error;
    return data;
  },

  async getDocumentEntities(docId: string) {
    const { data, error } = await supabase
      .from('extracted_entities')
      .select('*')
      .eq('document_id', docId);
    
    if (error) throw error;
    return data;
  }
};

export const templateApi = {
  async listTemplates(userId: string) {
    const { data, error } = await supabase
      .from('templates')
      .select('*')
      .eq('owner_id', userId)
      .order('created_at', { ascending: false });
    
    if (error) throw error;
    return data;
  },

  async uploadTemplate(file: File, userId: string) {
    const fileExt = file.name.split('.').pop();
    const fileName = `${userId}/templates/${Math.random().toString(36).substring(2, 15)}.${fileExt}`;
    const filePath = `templates/${fileName}`;

    const { error: uploadError } = await supabase.storage
      .from('document_storage')
      .upload(filePath, file);

    if (uploadError) throw uploadError;

    const { data, error } = await supabase
      .from('templates')
      .insert({
        owner_id: userId,
        name: file.name,
        type: fileExt || 'unknown',
        storage_path: filePath
      })
      .select()
      .maybeSingle();

    if (error) throw error;
    return data;
  }
};

export const taskApi = {
  async listTasks(userId: string) {
    const { data, error } = await supabase
      .from('fill_tasks')
      .select('*, templates(*)')
      .eq('owner_id', userId)
      .order('created_at', { ascending: false });
    
    if (error) throw error;
    return data;
  },

  async createTask(userId: string, templateId: string, documentIds: string[]) {
    const { data, error } = await supabase
      .from('fill_tasks')
      .insert({
        owner_id: userId,
        template_id: templateId,
        document_ids: documentIds,
        status: 'pending'
      })
      .select()
      .maybeSingle();
    
    if (error) throw error;
    return data;
  }
};
