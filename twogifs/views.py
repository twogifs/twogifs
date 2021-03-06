from uuid import uuid4

from werkzeug.exceptions import NotFound
from flask import (
    redirect,
    request,
    send_from_directory,
    session,
    render_template,
)

from .data import ImageRanking
from . import app
from .tracking import track_vote
from .spam_filter import (
    is_human,
    has_valid_session,
    rate_limit,
    is_rate_limited,
)

image_ranking = ImageRanking()


# Views
@app.route('/robots.txt')
@app.route('/favicon.ico')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


@app.route("/")
def index():
    # Get two random images
    images = image_ranking.get_image_sample()

    return render_template(
        'index.html',
        images=images,
        ranking=image_ranking.get_image_ranking()[:5],
    )


@app.route("/vote/<yay>/<nay>/")
def vote(yay, nay):
    if not has_valid_session(session):
        return redirect("/")

    rate_limit_key = sorted((yay, nay))

    if not is_rate_limited(session, rate_limit_key):
        try:
            image_ranking.image_retriever.get_image(yay)
            image_ranking.image_retriever.get_image(nay)
        except KeyError:
            raise NotFound()

        image_ranking.upvote_image(yay)
        image_ranking.downvote_image(nay)

        track_vote(request, session, yay, nay)

        rate_limit(session, rate_limit_key)

        session['score'] = session.get('score', 0) + 1
    else:
        app.logger.warning('Rate limiting for {}'.format(rate_limit_key))
    return redirect("/")


@app.route("/<left>")
def compare_one(left):
    images = [image_ranking.get_image_with_score(
        left)] + image_ranking.get_image_sample(1)
    return render_template(
        'index.html',
        images=images,
        ranking=image_ranking.get_image_ranking()[:5],
    )


@app.route("/<left>/<right>")
def compare_two(left, right):
    images = [
        image_ranking.get_image_with_score(left),
        image_ranking.get_image_with_score(right),
    ]
    return render_template(
        'index.html',
        images=images,
        ranking=image_ranking.get_image_ranking()[:5],
    )


@app.route("/ranking")
def ranking():
    return render_template(
        'ranking.html',
        ranking=image_ranking.get_image_ranking(),
    )


@app.route("/ping")
def ping():
    return "YESYES"


@app.before_request
def check_session():
    if not is_human(request):
        return
    elif not has_valid_session(session):
        create_session()


def create_session():
    session.permanent = True
    session['uid'] = str(uuid4())
