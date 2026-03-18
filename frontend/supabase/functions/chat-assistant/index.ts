import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders } from '../_shared/cors.ts';

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { messages, userId } = await req.json();
    if (!messages || !userId) throw new Error('Missing messages or userId');

    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

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
              content: `你是一个专业的文档智能交互助手。你的目标是协助用户完成文档管理、信息提取和表格填写。
你所在的系统支持：
1. 列出当前用户的文档列表。
2. 查看某个文档提取到的关键实体。
3. 协助用户通过自然语言发起文档编辑、排版等指令（当前模拟执行）。
请以专业且友好的语气回复。`
            },
            ...messages
          ]
        })
      }
    );

    const miniMaxData = await miniMaxResponse.json();
    if (!miniMaxResponse.ok) throw new Error('MiniMax chat failed');

    return new Response(JSON.stringify({ 
      choices: miniMaxData.choices 
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error in chat assistant:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
});
