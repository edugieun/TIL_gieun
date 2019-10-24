import hashlib
from IPython import embed
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_POST
from .models import Article, Comment, Hashtag
from .forms import ArticleForm, CommentForm

# Create your views here.
def index(request):
    # embed()
    # session 에 visits_num 키로 접근해 값을 가져온다.
    # visits_num은 기본적으로 존재하지 않은 키 이므로 키가 없다면(방문한적이 없다면) 0 값을 가져오도록 한다.
    visits_num = request.session.get('visits_num', 0)
    # 그리고 가져온 값은 session에 visits_num에 매번 1씩 증가한 값으로 할당한다. (유저의 다음 방문을 위해)
    request.session['visits_num'] = visits_num + 1
    # session data 안에 있는 특정 새로운 정보를 수정했다면 django는 수정한 사실을 알아채지 못하기 때문에 다음과 같이 설정.
    request.session.modified = True
    # embed()
    articles = Article.objects.all()
    context = {'articles': articles, 'visits_num': visits_num,}
    return render(request, 'articles/index.html', context)


@login_required
def create(request):
    # embed()
    if request.method == 'POST':
        # form 인스턴스를 생성하고 요청에 의한 데이터를 인자로 받는다. (binding 작업)
        # 이 처리과정은 binding 이라고 불리며 유효성 체크를 할 수 있도록 해준다.
        form = ArticleForm(request.POST) # request.POST로 데이터를 통째로 받아 알아서 매칭하게 해준다.
        # embed()
        # 유효성 검증
        # form 이 유효한지 체크한다. (ex. blank=False와 같은 DB와 관련된 유효성 내용들)
        if form.is_valid():
            article = form.save(commit=False)
            article.user = request.user
            article.save()
            # Hashtag는 글이 다 작성되고 저장된 후에 처리해야 한다.
            for word in article.content.split(): # content를 공백 기준으로 리스트로 변경
                if word.startswith('#'): # '#'으로 시작하는 요소만 선택
                    # get_or_create: 있으면 가져오고, 없으면 생성
                    # get_or_create는 튜플이기 때문에, 아래처럼 변수를 2개로 나누거나, 나중에 사용할 때 variable[0] 처럼 인덱스로 받아야 한다.
                    hashtag, created = Hashtag.objects.get_or_create(content=word)
                    article.hashtags.add(hashtag)
            return redirect(article)
            # 원래는 'articles:detail', article.pk 라고 써야 하지만 get_absolute_url을 적용하면 article 그냥 객체 이름만 넣어도 된다.
    else:   
        form = ArticleForm()
    context = {'form': form,}
    return render(request, 'articles/form.html', context) # 반드시 이 줄과 윗 줄은 if~else문 밖으로 나와야 한다.

    
def detail(request, article_pk):
    # try:
    #     article = Article.objects.get(pk=article_pk)
    # except Article.DoesNotExist:
    #     raise Http404('No Article matches the given query.')
    # context = {'article': article,}
    # return render(request, 'articles/detail.html', context)
    article = get_object_or_404(Article, pk=article_pk)
    comments =  article.comment_set.all() # article의 모든 댓글
    comment_form = CommentForm() # 댓글 form
    person = get_object_or_404(get_user_model(), pk=article.user_id)
    context = {'article': article, 'comment_form': comment_form, 'comments': comments, 'person': person,}
    return render(request, 'articles/detail.html', context)


@require_POST
def delete(request, article_pk):
    if request.user.is_authenticated:
        article = get_object_or_404(Article, pk=article_pk)
        if request.user == article.user:
            article.delete()
        else:
            return redirect(article)
    return redirect('articles:index')


@login_required
def update(request, article_pk):
    article = get_object_or_404(Article, pk=article_pk)
    if request.user == article.user:
        if request.method == 'POST':
            form = ArticleForm(request.POST, instance=article) # binding 작업 (instance : modelform에서 initial의 역할)
            if form.is_valid(): # 유효성 검증
                article = form.save()

                # HashTag
                article.hashtags.clear() # 해당 article의 hashtag 전체 삭제
                for word in article.content.split(): # content를 공백 기준으로 리스트로 변경
                    if word.startswith('#'):
                        hashtag, created = Hashtag.objects.get_or_create(content=word)
                        article.hashtags.add(hashtag)

                return redirect(article)
        else:
            # embed()
            # ArticleForm 을 초기화 (이전에 DB에 저장된 데이터를 넣어준 상태)
            # form = ArticleForm(initial={'title': article.title, 'content': article.content}) # initial : 기존의 값을 가져온다(딕셔너리 형태로!)
            # __dict__ : article 객체 데이터를 딕셔너리 자료형으로 변환
            # form = ArticleForm(initial=article.__dict__)
            form = ArticleForm(instance=article)
        # 위와 같이 복잡한 한 줄은 매직 머서드(__dict__)로 줄여서 쓸 수 있다.
        # 1. POST 방식일 때 넘어오는 form => 검증에 실패한 form(오류 메세지도 포함된 상태의 form)
        # 2. GET 방식일 때 넘어오는 form => 초기화된 form
    else:
        return redirect('articles:index')
    context = {'form': form, 'article': article,}
    return render(request, 'articles/form.html', context) # 서로 form을 쓰므로 create.html을 빌려와서 쓴다.(template은 공유하는 상태)


@require_POST
def comments_create(request, article_pk):
    if request.user.is_authenticated:
        comment_form = CommentForm(request.POST) # request.POST => POST방식으로 들어온 모든 데이터
        if comment_form.is_valid():
            # commit=False => 객체를 Create 하지만, db에 레코드는 작성하지 않는다.
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.article_id = article_pk
            comment.save()
            
    return redirect('articles:detail', article_pk)


@require_POST
def comments_delete(request, article_pk, comment_pk):
    if request.user.is_authenticated:
        comment = get_object_or_404(Comment, pk=comment_pk)
        if request.user == comment.user:
            comment.delete()
        return redirect('articles:detail', article_pk)
    return HttpResponse('You are Unauthorized', status=401)
    # 원래는 아래와 같이 작성
    # if request.user.is_authenticated:
    #     comment = get_object_or_404(Comment, pk=comment_pk)
    #     comment.delete()
    # return redirect('articles:detail', article_pk)

@login_required
def like(request, article_pk):
    article = get_object_or_404(Article, pk=article_pk)

    # 해당 게시글에 좋아요를 누른 사람들 중에서 현재 접속 유저가 있다면 좋아요를 취소(한번 더 누르면 취소
    # if request.user in article.like_users.all(): 이렇게 써도 되지만, django 문법이 속도가 더 빠르다.
    if article.like_users.filter(pk=request.user.pk).exists(): # get 대신 filter를 사용하는 이유는 get은 키가 없으면 오류 발생, filter는 키가 없어도 빈 스트링 값을 반환
        article.like_users.remove(request.user) # 좋아요 취소
    else:
        article.like_users.add(request.user) # 좋아요
    return redirect('articles:index')

@login_required
def follow(request, article_pk, user_pk):
    # 게시글 유저
    person = get_object_or_404(get_user_model(), pk=user_pk) # get_user_model은 항상 함수이기 때문에 get_user_model() 괄호를 꼭 붙인다.
    # 접속 유저
    user = request.user
    if person != user:
        # 내(user)가 게시글 유저(person) 팔로워 목록에 이미 존재 한다면,
        if person.followers.filter(pk=user.pk).exists():
            person.followers.remove(user)
        else:
            person.followers.add(user)
    return redirect('articles:detail', article_pk)



def hashtag(request, hash_pk):
    hashtag = get_object_or_404(Hashtag, pk=hash_pk)
    articles = hashtag.article_set.order_by('-pk')
    context = {
        'hashtag': hashtag,
        'articles': articles,
        }
    return render(request, 'articles/hashtag.html', context)