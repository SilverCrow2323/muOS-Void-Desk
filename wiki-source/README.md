# QWASAR Desk Wiki source pages

These Markdown pages are the source-controlled documentation for the QWASAR Desk GitHub Wiki. They are reviewed alongside the application source so the product manual, architecture and package instructions stay versioned together.

## One-time bootstrap

The repository Wiki must be initialized once in GitHub before its special `.wiki.git` repository exists.

1. Open https://github.com/SilverCrow2323/Void-Desk-Project/wiki
2. Select **Create the first page**.
3. Use the title **Home** and paste the contents of `wiki-source/Home.md`.
4. Save the page.

## Publish or refresh the Wiki

After the first Home page has been saved, clone the source repository on a PC and run:

~~~bash
sh tools/publish_wiki.sh
~~~

The publisher clones the special Wiki repository, copies the reviewed Markdown pages and sidebar, commits and pushes them using the Git credentials already configured on the PC. It does not modify the source repository.

**Current limitation:** this branch updates the source-controlled Wiki pages. The live GitHub Wiki has not yet been initialized through its one-time Home-page UI action, so the publisher cannot sync it until that action is completed.
