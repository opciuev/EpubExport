# EPUB Exporter v2.0 Testing Guide

## Testing Objectives

Verify if v2.0 resolves the issue of "content reduction after splitting by bookmarks" found in the original version.

## Environment Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install ebooklib pypandoc
```

### 2. Verify File Integrity
Ensure the following files exist:
- `epub_exporter.py` (original version)
- `epub_exporter_v2.py` (new version)
- `compare_versions.py` (comparison tool)
- `research_ebooklib.py` (structure analysis tool)

## Testing Steps

### Step 1: EPUB Structure Analysis
First, analyze your EPUB file structure to understand its internal organization:

```bash
python research_ebooklib.py your_book.epub
```

**Focus on:**
- Number of TOC items
- Number of Spine items
- Number of document items
- TOC-to-content mapping
- Presence of anchor splitting

### Step 2: Version Comparison Test
Run the comparison tool to compare extraction results from both versions:

```bash
python compare_versions.py your_book.epub
```

**Key metrics to check:**
- **Total content length**: Is v2 longer than v1?
- **Chapter count**: Is it reasonable?
- **Short chapters**: Did v2 reduce chapters <500 characters?
- **Duplicate content**: Did v2 reduce duplicates?
- **Content retention rate**: v2 percentage relative to v1

### Step 3: Detailed Verification
If comparison shows v2 improvements, perform detailed verification:

#### 3.1 Export with v1 (debug mode)
```bash
python test_content_extraction.py your_book.epub
```

#### 3.2 Export with v2 (debug mode)
```bash
python epub_exporter_v2.py your_book.epub -d
```

#### 3.3 Actual Export Test
```bash
# v1 export to output_v1 directory
python epub_exporter.py your_book.epub -o output_v1

# v2 export to output_v2 directory  
python epub_exporter_v2.py your_book.epub -o output_v2
```

### Step 4: Manual Verification
Compare exported files:

1. **File count comparison**
   - Check file counts in both output directories
   - Any significant differences?

2. **File size comparison**
   - Compare sizes of corresponding chapter files
   - Are v2 files generally larger?

3. **Content integrity check**
   - Randomly select several chapter files
   - Check if content is complete and reasonable
   - Any obvious truncation or duplication?

## Test Result Evaluation

### Success Criteria
v2 is considered successful if:

1. **Increased total content**: v2 total length ≥ v1 total length
2. **Reduced short chapters**: Significantly fewer short chapters
3. **Reduced duplicate content**: Fewer duplicate chapter groups
4. **Reasonable chapter count**: Chapter count within reasonable range
5. **Manual verification passes**: Exported files are complete and reasonable

### Failure Indicators
v2 has issues if:

1. **Reduced total content**: v2 total < 90% of v1 total
2. **Abnormal chapter count**: Too few (<3) or too many (>100) chapters
3. **Many short chapters**: Still many <500 character chapters
4. **New duplication issues**: v2 creates more duplicate content
5. **Manual verification fails**: Exported files have obvious problems

## Common Issue Troubleshooting

### Issue 1: Import Errors
```
ModuleNotFoundError: No module name 'xxx'
```
**Solution**: Install missing dependencies

### Issue 2: EPUB File Cannot Be Read
```
Cannot load EPUB file: xxx
```
**Solution**:
- Check if file path is correct
- Confirm file is valid EPUB format
- Try opening with other EPUB readers to verify

### Issue 3: Abnormal Comparison Results
If comparison tool shows abnormal results:
- Check if both versions run normally
- Review error messages in debug output
- Try testing with simpler EPUB files

## Test Report Template

After testing, please provide the following information:

```
EPUB File Information:
- Filename:
- File size:
- Expected chapter count:

Test Results:
- v1 total content length:
- v2 total content length:
- Content retention rate:
- v1 chapter count:
- v2 chapter count:
- v1 short chapter count:
- v2 short chapter count:

Conclusion:
- Did v2 solve the content reduction issue?
- Any new problems?
- Overall evaluation:

Specific Issues (if any):
- Describe discovered problems
- Provide relevant debug output
```

## Multi-file Testing Recommendations

For comprehensive verification, test with different types of EPUB files:

1. **Simple EPUB**: Clear chapter structure, no complex anchors
2. **Complex EPUB**: Multi-level TOC, uses anchor splitting
3. **Large EPUB**: Substantial content, long chapters
4. **Small EPUB**: Limited content, short chapters

Test at least 1-2 files of each type to ensure v2's universality.

## Feedback Method

After testing, please provide:
1. Test report (following above template)
2. Problematic EPUB files (if shareable)
3. Relevant debug output logs
4. Specific improvement suggestions

This allows me to further optimize the code based on actual test results.
