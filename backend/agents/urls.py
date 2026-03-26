from django.urls import path

from .views import (
    get_branches,
    create_branch_view,
    get_branch_files,
    upload_pdfs_view,
    rebuild_embeddings_view
)

urlpatterns = [

    path("branches/", get_branches),

    path("branches/create/", create_branch_view),

    path("branches/<str:branch>/files/", get_branch_files),

    path("upload-pdfs/", upload_pdfs_view),

    path("rebuild-embeddings/", rebuild_embeddings_view),

]