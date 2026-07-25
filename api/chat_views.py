from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .chat_models import ChatConversation, ChatMessage
from .llm_service import process_message
from .report_analyzer import analyze_report


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get('message', '').strip()
        conversation_id = request.data.get('conversation_id')

        if not user_message:
            return Response({'error': 'Message is required'}, status=400)

        if conversation_id:
            conversation = get_object_or_404(
                ChatConversation, id=conversation_id, user=request.user
            )
        else:
            title = user_message[:50] + ('...' if len(user_message) > 50 else '')
            conversation = ChatConversation.objects.create(
                user=request.user,
                title=title
            )

        ChatMessage.objects.create(
            conversation=conversation,
            role='user',
            content=user_message
        )

        history = list(
            ChatMessage.objects.filter(conversation=conversation)
            .values('role', 'content')
        )

        try:
            result = process_message(user_message, history)
        except Exception as e:
            return Response({
                'error': f'AI service error: {str(e)}',
                'conversation_id': conversation.id
            }, status=500)

        ChatMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=result['response'],
            metadata={
                'db_results': result['db_results'],
                'symptoms_found': result['symptoms_found'],
                'intent': result['intent']
            }
        )

        conversation.save()

        return Response({
            'response': result['response'],
            'conversation_id': conversation.id,
            'db_results': result['db_results'],
            'symptoms_found': result['symptoms_found'],
            'intent': result['intent']
        })


class ChatReportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('file')
        report_name = request.data.get('report_name', 'Medical Report')
        conversation_id = request.data.get('conversation_id')

        if not file:
            return Response({'error': 'File is required'}, status=400)

        if conversation_id:
            conversation = get_object_or_404(
                ChatConversation, id=conversation_id, user=request.user
            )
        else:
            conversation = ChatConversation.objects.create(
                user=request.user,
                title=f"Report: {report_name}"
            )

        ChatMessage.objects.create(
            conversation=conversation,
            role='user',
            content=f"📎 Uploaded report: {report_name}"
        )

        try:
            report_result = analyze_report(file, 'other', report_name)
        except Exception as e:
            return Response({
                'error': f'Report analysis failed: {str(e)}',
                'conversation_id': conversation.id
            }, status=500)

        analysis_context = f"Medical Report Analysis for '{report_name}':\n"
        if report_result.get('extracted_values'):
            analysis_context += f"Extracted values: {report_result['extracted_values']}\n"
        if report_result.get('analysis_result'):
            analysis_context += f"Analysis: {report_result['analysis_result']}\n"
        if report_result.get('ai_suggestions'):
            analysis_context += f"Suggestions: {report_result['ai_suggestions']}\n"

        history = list(
            ChatMessage.objects.filter(conversation=conversation)
            .values('role', 'content')
        )

        try:
            from .llm_service import chat_with_llm
            response = chat_with_llm(
                f"Analyze this medical report and provide health insights, food recommendations, and medicine suggestions:\n\n{analysis_context}",
                history,
                analysis_context,
                'general'
            )
        except Exception as e:
            response = f"**Report Analysis:**\n\n{analysis_context}\n\nPlease consult a doctor for detailed interpretation of these results."

        ChatMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=response,
            metadata={
                'report_analysis': report_result,
                'intent': 'report_analysis'
            }
        )

        conversation.save()

        return Response({
            'response': response,
            'conversation_id': conversation.id,
            'report': report_result
        })


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        conversations = ChatConversation.objects.filter(
            user=request.user
        ).annotate(
            message_count=Count('messages')
        ).values('id', 'title', 'created_at', 'updated_at', 'message_count')

        result = [
            {
                'id': c['id'],
                'title': c['title'],
                'created_at': c['created_at'],
                'updated_at': c['updated_at'],
                'message_count__count': c['message_count']
            }
            for c in conversations
        ]

        return Response(result)

    def delete(self, request):
        conversation_id = request.data.get('id')
        if conversation_id:
            get_object_or_404(
                ChatConversation, id=conversation_id, user=request.user
            ).delete()
        return Response({'success': True})


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conversation = get_object_or_404(
            ChatConversation, id=pk, user=request.user
        )
        messages = ChatMessage.objects.filter(
            conversation=conversation
        ).values('role', 'content', 'metadata', 'created_at')

        return Response({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at,
            'messages': list(messages)
        })

    def delete(self, request, pk):
        get_object_or_404(
            ChatConversation, id=pk, user=request.user
        ).delete()
        return Response({'success': True})
