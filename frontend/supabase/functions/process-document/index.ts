import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders } from '../_shared/cors.ts';
import * as XLSX from 'https://esm.sh/xlsx@0.18.5';
import * as mammoth from 'https://esm.sh/mammoth@1.5.1';

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { documentId } = await req.json();
    if (!documentId) throw new Error('Missing documentId');

    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get document details
    const { data: document, error: docError } = await supabase
      .from('documents')
      .select('*')
      .eq('id', documentId)
      .single();

    if (docError || !document) throw new Error('Document not found');

    // Download file
    const { data: fileData, error: dlError } = await supabase.storage
      .from('document_storage')
      .download(document.storage_path);

    if (dlError || !fileData) throw new Error('Failed to download file');

    const arrayBuffer = await fileData.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    let extractedText = '';

    // Parse file based on type
    const fileExt = document.type.toLowerCase();
    if (fileExt === 'txt' || fileExt === 'md') {
      extractedText = new TextDecoder().decode(uint8Array);
    } else if (fileExt === 'docx') {
      const result = await mammoth.extractRawText({ arrayBuffer });
      extractedText = result.value;
    } else if (fileExt === 'xlsx' || fileExt === 'xls') {
      const workbook = XLSX.read(arrayBuffer, { type: 'array' });
      extractedText = workbook.SheetNames.map(name => {
        const sheet = workbook.Sheets[name];
        return XLSX.utils.sheet_to_txt(sheet);
      }).join('\n\n');
    } else {
      throw new Error(`Unsupported file type: ${fileExt}`);
    }

    if (!extractedText.trim()) throw new Error('Document is empty');

    // Call MiniMax for entity extraction
    const miniMaxApiKey = Deno.env.get('INTEGRATIONS_API_KEY');
    const miniMaxResponse = await fetch(
      'https://app-a6ww9j3ja3nl-api-Aa2PqMJnJGwL-gateway.appmiaoda.com/v1/text/chatcompletion_v2',
      {
        method: 'POST',
        headers: {
          'X-Gateway-Authorization': `Bearer ${miniMaxApiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'MiniMax-M2.5',
          messages: [
            {
              role: 'system',
              content: '你是一个文档信息提取专家。请从提供的文档内容中提取关键实体信息（如姓名、日期、金额、项目名称、地址、关键指标等）。输出格式必须为 JSON 数组，包含 entity_type, entity_value, confidence 三个字段。'
            },
            {
              role: 'user',
              content: `文档内容如下：\n\n${extractedText.slice(0, 15000)}` // Limit text for token budget
            }
          ],
          response_format: {
            type: 'json_schema',
            json_schema: {
              name: 'extracted_entities',
              schema: {
                type: 'object',
                properties: {
                  entities: {
                    type: 'array',
                    items: {
                      type: 'object',
                      properties: {
                        entity_type: { type: 'string' },
                        entity_value: { type: 'string' },
                        confidence: { type: 'number' }
                      },
                      required: ['entity_type', 'entity_value']
                    }
                  }
                }
              }
            }
          }
        })
      }
    );

    const miniMaxData = await miniMaxResponse.json();
    if (!miniMaxResponse.ok) {
      console.error('MiniMax Error:', miniMaxData);
      throw new Error('MiniMax extraction failed');
    }

    const extractionResult = JSON.parse(miniMaxData.choices[0].message.content);
    const entities = extractionResult.entities || [];

    // Save entities
    if (entities.length > 0) {
      const entitiesToInsert = entities.map((e: any) => ({
        document_id: documentId,
        entity_type: e.entity_type,
        entity_value: e.entity_value,
        confidence: e.confidence || 1.0
      }));

      await supabase.from('extracted_entities').insert(entitiesToInsert);
    }

    // Update document
    await supabase.from('documents').update({
      content_text: extractedText,
      status: 'completed'
    }).eq('id', documentId);

    return new Response(JSON.stringify({ success: true, entities }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error processing document:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
});
