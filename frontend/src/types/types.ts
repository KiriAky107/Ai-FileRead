export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          email: string | null;
          phone: string | null;
          role: 'user' | 'admin';
          created_at: string | null;
        };
      };
      documents: {
        Row: {
          id: string;
          owner_id: string;
          name: string;
          type: string;
          storage_path: string;
          content_text: string | null;
          metadata: any;
          status: string;
          created_at: string | null;
          extracted_entities?: any[];
        };
      };
      extracted_entities: {
        Row: {
          id: string;
          document_id: string;
          entity_type: string;
          entity_value: string;
          confidence: number | null;
          created_at: string | null;
        };
      };
      templates: {
        Row: {
          id: string;
          owner_id: string;
          name: string;
          type: string;
          storage_path: string;
          created_at: string | null;
        };
      };
      fill_tasks: {
        Row: {
          id: string;
          owner_id: string;
          template_id: string;
          document_ids: string[];
          status: string;
          result_path: string | null;
          error_message: string | null;
          created_at: string | null;
          templates?: any;
        };
      };
    };
  };
}

export type Profile = Database['public']['Tables']['profiles']['Row'];
export type Document = Database['public']['Tables']['documents']['Row'];
export type ExtractedEntity = Database['public']['Tables']['extracted_entities']['Row'];
export type Template = Database['public']['Tables']['templates']['Row'];
export type FillTask = Database['public']['Tables']['fill_tasks']['Row'];

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  id: string;
  created_at: string;
}
