import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders } from '../_shared/cors.ts';

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { taskId } = await req.json();
    if (!taskId) throw new Error('Missing taskId');

    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get task and documents
    const { data: task, error: taskError } = await supabase
      .from('fill_tasks')
      .select('*, templates(*)')
      .eq('id', taskId)
      .single();

    if (taskError || !task) throw new Error('Task not found');

    const { data: entities, error: entitiesError } = await supabase
      .from('extracted_entities')
      .select('*')
      .in('document_id', task.document_ids);

    if (entitiesError) throw new Error('Failed to fetch entities');

    // Aggregate entities for context
    const context = entities.map(e => `${e.entity_type}: ${e.entity_value}`).join('\n');

    // Get template content (assume docx/xlsx text extraction for template)
    // Actually, MiniMax can help generate the final filled content if we provide the template structure
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
              content: '你是一个专业的文档处理助手。请根据提供的源数据实体，自动填充到给定的表格模板中。生成的文档应当格式严谨，满足业务应用需求。'
            },
            {
              role: 'user',
              content: `源数据信息如下：\n\n${context}\n\n模板名称：${task.templates.name}\n模板类型：${task.templates.type}\n\n请生成填充后的文档内容预览（以 Markdown 格式呈现，确保包含所有源数据中的关键指标）。`
            }
          ]
        })
      }
    );

    const miniMaxData = await miniMaxResponse.json();
    if (!miniMaxResponse.ok) throw new Error('MiniMax filling failed');

    const resultText = miniMaxData.choices[0].message.content;

    // Update task
    const { error: updateError } = await supabase
      .from('fill_tasks')
      .update({
        status: 'completed',
        result_path: `results/${taskId}.md` // Save as md for simplicity in this demo
      })
      .eq('id', taskId);

    // Store result in storage
    await supabase.storage
      .from('document_storage')
      .upload(`results/${taskId}.md`, new Blob([resultText], { type: 'text/markdown' }));

    return new Response(JSON.stringify({ success: true, result: resultText }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error filling template:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
});
