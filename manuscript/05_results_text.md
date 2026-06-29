# Results: Text Scale, Visual Evidence, and Cross-Modal Diagnostics {#sec:results_text}

This section reports analysis outputs over the acquired local corpus. Because only {{WORKS_WITH_TEXT}} of {{WORKS_PRESENT}} local works contain text, textual metrics describe a substantial but incomplete subset. Likewise, image and cross-modal metrics describe the {{WORKS_WITH_IMAGES}} image-bearing works and the {{WORKS_WITH_BOTH}} works with both modalities. The results function as a materials meta-analysis: they show which local evidence can support text diagnostics, image diagnostics, and joint inspection before any reader treats those diagnostics as literary interpretation. The figures should therefore be read as interpretive displays of the saved evidence state, not as stylistic periodization, iconographic classification, or a model of Blake as a whole [@drucker2011graphical; @drucker2020visualization].

## Lexical Results: Text Scale, Vocabulary, and Phrase Diagnostics

The text-bearing subset contains {{WORDS_TOTAL}} total words. When per-work unique counts are summed, the subset contains {{UNIQUE_WORDS_TOTAL}} unique-word observations; this is a per-work vocabulary diagnostic rather than a deduplicated corpus lexicon. Per-work word counts range from {{WORDS_MIN}} to {{WORDS_MAX}} words. [@fig:word_counts] plots the largest text-bearing works, and [@tbl:top_texts] records the same top rows with unique-word and image-link counts.

![Largest local text-bearing corpus records by word count. Bars measure acquired transcription length, showing which source-backed text files dominate aggregate vocabulary and theme diagnostics; works without local text are excluded.](../output/figures/word_counts.png){#fig:word_counts}

| Work | Words | Unique words | Vocab richness | Images |
|---|---:|---:|---:|---:|
{{TOP_TEXT_TABLE_ROWS}}

: Largest text-bearing local works. The image column indicates whether a text-heavy work also participates in cross-modal analysis. {#tbl:top_texts}

Vocabulary richness averages {{VOCAB_RICHNESS_MEAN}} across text-bearing works and ranges from {{VOCAB_RICHNESS_MIN}} to {{VOCAB_RICHNESS_MAX}}. [@fig:vocab_richness] plots type-token ratio against text length. The downward shape is expected for length-sensitive type-token ratios and should be treated as a diagnostic of metric behavior over the acquired text set, not as a global claim about Blake's vocabulary [@tweediebaayen1998lexical; @mccarthyjarvis2010lexical; @jockers2013macroanalysis].

![Vocabulary richness versus text length for local text-bearing records. Each point is one acquired transcription; the log-scaled x-axis supports comparison across text sizes, while the metric remains bounded to local text evidence and is not a Blake-wide stylistic claim.](../output/figures/vocab_richness.png){#fig:vocab_richness}

The lexical-signature artifact uses `{{LEXICAL_SIGNATURE_METHOD}}` over {{LEXICAL_TEXT_WORKS}} text-bearing works. It records {{LEXICAL_TOKEN_COUNT}} stopword-filtered lexical tokens and {{LEXICAL_DISTINCT_TERMS}} distinct terms, with mean lexical density {{LEXICAL_DENSITY_MEAN}}. The highest-count terms include {{LEXICAL_TOP_TERMS_CSV}}, and frequent adjacent-term phrases include {{LEXICAL_TOP_BIGRAMS_CSV}}. [@fig:lexical_signature] visualizes the leading terms and phrases, while [@tbl:lexical_signature] preserves their document-frequency context.

![Stopword-filtered lexical signature for local transcriptions. Term and phrase counts are generated from the acquired text files used elsewhere in the manuscript, so the denominator is the local text subset rather than unsourced Blake-wide vocabulary.](../output/figures/lexical_signature.png){#fig:lexical_signature}

| Term | Count | Documents |
|---|---:|---:|
{{LEXICAL_SIGNATURE_TABLE_ROWS}}

: Leading stopword-filtered corpus terms. Document counts show whether a term is corpus-wide or concentrated in a small number of transcriptions. {#tbl:lexical_signature}

## Embedding Results: PCA/LSA Structure and Entity Extraction

The text layer supports a more explicitly natural-language analysis than word counts alone. The manuscript pipeline builds a {{NLP_EMBEDDING_METHOD}} from {{NLP_EMBEDDING_WORKS}} local transcriptions and a {{NLP_EMBEDDING_FEATURES}}-term vocabulary. [@fig:nlp_embedding_pca] projects that space onto the leading axes: PC1 accounts for {{NLP_PCA_PC1_PCT}}% of the TF-IDF variance, PC2 accounts for {{NLP_PCA_PC2_PCT}}%, and the plotted plane accounts for {{NLP_PCA_TOTAL_PCT}}%. This is a bounded corpus diagnostic, not a semantic map of every Blake work, because texts absent from local storage cannot enter the vector space [@biber1993representativeness; @bode2018world]. Its value is procedural: it makes the acquired text set explorable and contestable, the way algorithmic criticism and computer-assisted interpretation treat computation as a partner in reading rather than an oracle [@ramsay2011readingmachines; @rockwellsinclair2016hermeneutica].

![Latent text embedding from local transcriptions. The map projects {{NLP_EMBEDDING_WORKS}} text-bearing corpus records from a {{NLP_EMBEDDING_FEATURES}}-term TF-IDF matrix onto deterministic PCA/LSA axes; missing and image-only works do not enter this textual geometry.](../output/figures/nlp_embedding_pca.png){#fig:nlp_embedding_pca}

The leading vocabulary terms also make the projection auditable. PC1 is driven by terms such as {{NLP_EMBEDDING_TOP_TERMS_PC1}}, while PC2 is driven by terms such as {{NLP_EMBEDDING_TOP_TERMS_PC2}}. These terms should be read as feature loadings over local transcriptions: they help locate clusters, outliers, transcription effects, and acquisition artifacts, but they do not by themselves establish interpretive periodization.

Entity extraction adds a second kind of linguistic evidence. Across {{ENTITY_ANALYSIS_ARTIFACTS}} ontological-analysis artifacts, {{ENTITY_WORKS_WITH_ENTITIES}} works currently contribute named-entity evidence. The extraction layer records {{ENTITY_MENTION_COUNT}} entity mentions across {{ENTITY_DISTINCT_COUNT}} distinct normalized strings and {{ENTITY_TYPE_COUNT}} entity labels, including {{ENTITY_LABELS_CSV}}. The most frequent normalized strings are {{ENTITY_TOP_CSV}}. This is an index into person, place, mythic, and textual reference patterns, but it still requires human review because Blakean names, plate captions, and editorial metadata can blur the boundary between character, place, title, and bibliographic entity.

The per-work text-analysis artifacts broaden the picture further: {{TEXT_ANALYSIS_ARTIFACTS}} artifacts carry sentiment and readability diagnostics, with {{SENTIMENT_POSITIVE_WORKS}} positive, {{SENTIMENT_NEUTRAL_WORKS}} neutral, and {{SENTIMENT_NEGATIVE_WORKS}} negative sentiment classifications in the reported run. The mean Flesch reading-ease score is {{READABILITY_FLESCH_MEAN}}, and topic extraction emitted {{TOPIC_MODEL_COMPONENTS}} topic components across local text-analysis artifacts. These values help locate works for close reading and QA, but the manuscript treats them as computational descriptors rather than as stand-alone literary judgments [@flesch1948new; @panglee2008sentiment; @kimklinger2019sentiment; @blei2012topic; @ramsay2011readingmachines].

## Theme-Graph Results: A Navigable Index of Blake Motifs

The work-theme graph contains {{NETWORK_NODES}} nodes and {{NETWORK_EDGES}} edges, including {{THEME_COUNT}} theme nodes. [@fig:theme_network] summarizes the most frequent themes by work-theme links. The graph indexes how the acquired corpus is currently organized, but it inherits the corpus evidence boundary: manuscript targets with missing text cannot contribute textual entities until their transcriptions are acquired [@newman2010networks; @weingart2011networks; @moretti2011network].

![Theme frequencies in the generated work-theme graph. Bars count current local work-theme links from serialized analysis artifacts; the graph is an index over acquired evidence, not a settled thematic hierarchy for Blake's complete oeuvre.](../output/figures/theme_network.png){#fig:theme_network}

## Image-Linkage Results: Work-Level Cross-Modal Evidence

The visual subset contains {{TOTAL_IMAGES}} local image records linked across {{LINKED_WORKS}} works. [@fig:text_image_linkage] shows the works with the most local image evidence, while [@tbl:top_images] records whether those image-rich works also carry text. Image-bearing means that at least one local image record is linked to a work; object-depth mirroring is measured separately in the supplement. In this run the image-depth dataset records {{IMAGE_DEPTH_WORKS}} works, {{IMAGE_DEPTH_RESOLVED_OBJECTS}} resolved Archive object candidates, and {{IMAGE_DEPTH_DOWNLOADED_IMAGES}} downloaded local object images. These counts support distant-viewing style inventory and QA, but they still do not imply full copy-, plate-, object-, or manifest-level completeness outside the discoverable Archive API paths used by the command [@butlin1981paintings; @bindman1978graphic; @viscomi1993blake; @arnoldtilton2019distantviewing; @weverssmits2020visualdigitalturn].

![Local works with the most linked image evidence. Bars count locally stored image records by work; color distinguishes records that also have local text, making the text-image comparison subset explicit.](../output/figures/text_image_linkage.png){#fig:text_image_linkage}

[@fig:text_image_density] adds the complementary view: text length is plotted against linked local image count, with color encoding lexical density. This makes the joint analytical surface visible instead of implying that every text-bearing work is equally visual or that every image-bearing work has enough transcription evidence for language analysis.

![Text-image density across local text-bearing records. Each point is a work with local text; x encodes transcription length, y encodes linked local image files, and color encodes lexical density, so image-only works and remote-only objects remain outside this plot.](../output/figures/text_image_density.png){#fig:text_image_density}

| Work | Images | Has text |
|---|---:|---|
{{TOP_IMAGE_TABLE_ROWS}}

: Local works with the most image evidence. Rows with text available are candidates for joint text-image reading; rows without text remain visual-evidence records only. {#tbl:top_images}

The corpus supports cross-modal inspection for {{WORKS_WITH_BOTH}} works. It also supports an opt-in Archive object-image mirror whose depth is reported in [@fig:image_depth_by_work] and [@fig:image_depth_by_area]. The result remains a descriptive materials corpus: text, image, and joint analyses are tied to recorded local evidence, while object-depth counts are bounded by discoverable Archive work/copy metadata and local download success [@mitchell1994picture; @drucker2011graphical; @drucker2020visualization; @arnoldtilton2019distantviewing]. This is the appropriate level of claim for a corpus-governance paper: the pipeline identifies where cross-modal reading is possible and where the evidence surface is still too thin.
