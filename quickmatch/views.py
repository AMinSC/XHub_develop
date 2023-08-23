from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from rest_framework import status, filters
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Meeting, MeetingMembers, MeetingChat
from .serializers import MeetingSerializer, MeetingChangeSerializer

import io
from rest_framework.parsers import JSONParser
from django.contrib.auth import get_user_model
User = get_user_model()


class CreateMeeting(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({"message": "get method is not available."})
    
    def post(self, request):
        qdict = request.data
        serializer = MeetingSerializer(data=qdict)
        
        if serializer.is_valid():
            
            data = serializer.data
            quickmatch = serializer.create(data) # 오브젝트 생성만
            quickmatch.organizer = request.user
            
            category_list = [i[0] for i in Meeting.CATEGORY_CHOICE]
            gender_list = [i[0] for i in Meeting.GENDER_CHOICE]
            status_list = [i[0] for i in Meeting.STATUS_CHOICE]
            
            # 카테고리, 성별제한, 상태 default설정. (목록에 없는 값은 is_valid False)
            if not data.get('category', None):
                quickmatch.category = category_list[0]
                
            if not data.get('gender_limit', None):
                quickmatch.category = gender_list[2]
                
            if not data.get('status', None):
                quickmatch.status = status_list[0]
                
            if not data.get('max_participants', None):
                quickmatch.max_participants = 10

            quickmatch.save() # 오브젝트 저장
            return Response({"message": "create sucess!", "meeting": repr(quickmatch)}, status=status.HTTP_200_OK)
        
        return Response({"message": "data is not available", "error": serializer.errors})


class DeleteMeeting(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, quickmatchId):
        return Response({"message": "GET method is not available."})
    
    def post(self, request, quickmatchId):
        
        quickmatch = get_object_or_404(Meeting, pk=quickmatchId)
        if quickmatch.organizer==request.user:
            result = {"message": "meeting deleted!",
                        "meeting": repr(quickmatch),}
            quickmatch.delete()
            return Response(result, status=status.HTTP_200_OK)
        
        return Response({"message": "Meeting is not exists"}, status=status.HTTP_404_NOT_FOUND)


class JoinMeeting(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, quickmatchId):
        return Response({"message": "GET method is not available."})
    
    def post(self, request, quickmatchId):
        
        quickmatch = get_object_or_404(Meeting, pk=quickmatchId)
        
        if quickmatch.organizer == request.user:
            return Response({"message": "적절하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if quickmatch.current_participants == quickmatch.max_participants:
                return Response({"message": "the Meeting is full. You cannot join to this QuickMatch."})
            else:
                quickmatch.add_participant()
                quickmatch.save()
                
                # meeting member 추가
                MeetingMembers.objects.create(quickmatch=quickmatch, attendant=request.user)
                return Response({"message": "join success!"})


class ChangeMeetingStatus(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, quickmatchId):
        return Response({"message": "GET method is not available."})
    
    def post(self, request, quickmatchId):
        
        quickmatch = get_object_or_404(Meeting, pk=quickmatchId)
        
        if quickmatch.organizer == request.user:
            data = request.data.dict() #Querydict(수정불가)를 dict로 바꿔줌.
            if not data.get('title', None):
                data.update({'title': quickmatch.title})
                print(data.get('title', 'nono'))
                
            serializer = MeetingChangeSerializer(data=data)

            if serializer.is_valid():
                data = serializer.data
                serializer.update(quickmatch, data)
                return Response({"message": "QuickMatch config are Changed."})
        
        else:
            return Response({"message": "적절하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

class MeetingSearchView(ListAPIView):
    serializer_class = MeetingSerializer
    permission_classes = [AllowAny,]

    def get_queryset(self):
        queryset = Meeting.objects.all()

        category = self.request.query_params.get('category', None)
        status = self.request.query_params.get('status', None)

        if category:
            queryset = queryset.filter(category=category)
        
        if status:
            queryset = queryset.fliter(status=status)

        # GET 파라미터로부터 검색어를 가져옵니다.
        query = self.request.GET.get('search', '')
        
        # 검색어를 공백 기준으로 분리합니다.
        terms = query.split()

        # 각 단어에 대한 Q 객체를 생성합니다.
        q_objects = Q()

        for term in terms:
            q_objects |= Q(title__icontains=term) | Q(location__icontains=term)
        
        return queryset.filter(q_objects)
