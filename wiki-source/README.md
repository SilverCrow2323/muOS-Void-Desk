# GitHub Wiki source pages

These Markdown pages are prepared for the repository's actual GitHub Wiki. They are kept in wiki-source/ so that changes can be reviewed alongside source code.

## One-time bootstrap

GitHub Wiki is enabled for this repository, but GitHub has not initialized the special .wiki repository yet. It creates the repository after the first page is saved.

1. Open https://github.com/SilverCrow2323/Void-Desk-Project/wiki
2. Select **Create the first page**.
3. Use the title **Home** and paste the contents of wiki-source/Home.md.
4. Save the page.

## Publish the remaining pages

After the Home page has been created, clone the source repository on your PC and run:

~~~bash
sh tools/publish_wiki.sh
~~~

The script clones the .wiki.git repository, copies the prepared Markdown pages (including the sidebar), commits and pushes them using the Git credentials already configured on your machine. It does not modify the source repository.

**Current limitation:** the GitHub Wiki itself is not initialized until the first page is saved in the GitHub UI. The source pages and publisher are prepared here, but the one-time creation of the first Home page still needs that browser action.
