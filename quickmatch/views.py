from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import (
    Meeting,
    MeetingMembers,
    MeetingRoom,
    UserEvaluation,
)
from .serializers import (
    MeetingSerializer,
    MeetingChangeSerializer,
    MeetingDetailSerializer,
    UserEvaluationSerializer,
)

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
            quickmatch = serializer.create(data)  # 오브젝트 생성만
            quickmatch.organizer = request.user
            
            category_list = [i[0] for i in Meeting.CATEGORY_CHOICE]
            gender_list = [i[0] for i in Meeting.GENDER_CHOICE]
            status_list = [i[0] for i in Meeting.STATUS_CHOICE]
            
            # 카테고리, 성별제한, 상태 default설정. (목록에 없는 값은 is_valid False)
            if not data.get('category', None):
                quickmatch.category = category_list[0]
                
            if not data.get('gender_limit', None):
                quickmatch.gender_limit = gender_list[2]
                
            if not data.get('status', None):
                quickmatch.status = status_list[0]
                
            if not data.get('max_participants', None):
                quickmatch.max_participants = 10

            quickmatch.save()  # 오브젝트 저장
            
            # 모임 생성자를 멤버에 추가
            MeetingMembers.objects.create(quickmatch=quickmatch, attendant=quickmatch.organizer)
            
            MeetingRoom.objects.create(meeting=quickmatch, name=f"{quickmatch.title}_chatroom", host=quickmatch.organizer)
            
            return Response({"message": "create success!", "meeting": repr(quickmatch)}, status=status.HTTP_200_OK)
        
        return Response({"message": "data is not available", "error": serializer.errors})


class DeleteMeeting(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, quickmatchId):
        return Response({"message": "GET method is not available."})
    
    def post(self, request, quickmatchId):
        
        quickmatch = get_object_or_404(Meeting, pk=quickmatchId)
        if quickmatch.organizer == request.user:
            result = {"message": "meeting deleted!",
                        "meeting": repr(quickmatch)}
            
            quickmatch.delete()
            return Response(result, status=status.HTTP_200_OK)
        
        return Response({"message": "Meeting is not exists"}, status=status.HTTP_404_NOT_FOUND)


class JoinMeeting(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, quickmatchId):
        return Response({"message": "GET method is not available."})
    
    def post(self, request, quickmatchId):
        
        quickmatch = get_object_or_404(Meeting, pk=quickmatchId)
        user = request.user
        
        if quickmatch.organizer == user:
            return Response({"message": "적절하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if quickmatch.current_participants == quickmatch.max_participants:
                return Response({"message": "the Meeting is full. You cannot join to this QuickMatch."})
            
            member_valid = MeetingMembers.objects.filter(quickmatch=quickmatch, attendant=user).exists()
            
            if member_valid:
                return Response({"message": f"{user} is already joined."})
            
            quickmatch.add_participant()
            quickmatch.save()
            MeetingMembers.objects.create(quickmatch=quickmatch, attendant=user)
            
            return Response({"message": "join success!"})


class LeaveMeeting(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, quickmatchId):
        return Response({"message": "GET method is not available."})
    
    def post(self, request, quickmatchId):
        quickmatch = get_object_or_404(Meeting, pk=quickmatchId)
        user = request.user
        
        if quickmatch.organizer == user:
            return Response({"message": "적절하지 않은 요청입니다. 퀵매치 삭제를 해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            member_exists = MeetingMembers.objects.filter(quickmatch=quickmatch, attendant=user).exists()
            if not member_exists:
                return Response({"message": "You are not a member of this match."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                quickmatch.remove_participant()
                quickmatch.save()
                
                member = MeetingMembers.objects.get(quickmatch=quickmatch, attendant=user)
                member.delete()
            
                return Response({"message": "you leave this match!"})


class ChangeMeetingStatus(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, quickmatchId):
        return Response({"message": "GET method is not available."})
    
    def post(self, request, quickmatchId):
        
        quickmatch = get_object_or_404(Meeting, pk=quickmatchId)
        
        if quickmatch.organizer == request.user:
            newStatus = request.data.get('status')
            if newStatus and newStatus in dict(Meeting.STATUS_CHOICE):
                quickmatch.status = newStatus
                quickmatch.save()
                return Response({"message": f"회의 상태가 {newStatus}로 변경되었습니다."})

            else:
                return Response({"message": "제공된 상태가 유효하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "부적절한 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)


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


class MeetingListView(ListCreateAPIView):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    permission_classes = [AllowAny,]


class MeetingDetailView(RetrieveAPIView):
    queryset = Meeting.objects.all()
    serializer_class = MeetingDetailSerializer
    permission_classes = [AllowAny,]
    lookup_field = 'pk'
    lookup_url_kwarg = 'quickmatchId'



class EvaluateMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, member_id, meeting_id):
        member = get_object_or_404(User, id=member_id)
        meeting = get_object_or_404(Meeting, id=meeting_id)

        if not meeting.meeting_member.filter(id=request.user.id).exists():
            return Response({'status': '멤버만 평가할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.id == member_id:
            return Response({'status': '본인을 평가할 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 해당 멤버와 모임에 대한 평가가 이미 있는지 확인
        evaluation_exists = UserEvaluation.objects.filter(
            evaluator=request.user, 
            evaluated=member, 
            meeting=meeting
        ).exists()

        if not evaluation_exists and meeting.can_evaluate:
            member.activity_point += 3
            member.save()
            meeting.can_evaluate = False
            meeting.save()

            UserEvaluation.objects.create(
                evaluator=request.user,
                evaluated=member,
                meeting=meeting,
                is_positive=True  # 이 경우 평가가 항상 긍정적이라고 가정
            )
            return Response({'status': 'success'}, status=status.HTTP_200_OK)

        return Response({'status': '이미 평가되었거나 허용되지 않음'}, status=status.HTTP_400_BAD_REQUEST)


class JoinMeetingRoom(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, quickmatchId):
        meeting = get_object_or_404(Meeting, pk=quickmatchId)
        user = request.user
        result = MeetingRoom.objects.filter(meeting=meeting).exists()
        
        if result:
            meeting_room = meeting.meetingroom
            try:
                meeting_room.current_users.add(user)
                return Response({"message": f"you join to {meeting_room.name} meeting chat room successful."}, status=status.HTTP_200_OK)
            except TypeError:
                return Response({"message": "wrong addition."})
        
        return Response({"message": "meetingroom is not exist."}, status=status.HTTP_400_BAD_REQUEST)


class LeaveMeetingRoom(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, quickmatchId):
        meeting = get_object_or_404(Meeting, pk=quickmatchId)
        user = request.user
        result = MeetingRoom.objects.filter(meeting=meeting).exists()
        
        if result:
            meeting_room = meeting.meetingroom
            try:
                meeting_room.current_users.remove(user)
                
                return Response({"message": f"{meeting_room.current_users.all()}"}, status=status.HTTP_200_OK)
            except TypeError:
                return Response({"message": "wrong addition."})
        
        return Response({"message": "meetingroom is not exist."}, status=status.HTTP_400_BAD_REQUEST)


class IsMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        user = request.user
        meeting = get_object_or_404(Meeting, pk=meeting_id)

        # 사용자가 지정된 회의의 회원인지 확인
        is_member = meeting.meeting_member.filter(id=user.id).exists()

        return Response({'is_member': is_member})
