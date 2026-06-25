# DRS v3 - Document Reconstruction & Translation System

## 1. Tóm tắt dự án

DRS v3 là một nền tảng hỗ trợ dịch thuật và bản địa hóa tài liệu bằng AI, tập trung vào hai nhóm nội dung chính:

- Văn bản dài: truyện chữ, tài liệu, bản thảo, markdown.
- Hình ảnh truyện tranh: manga, comic, webtoon có bong bóng thoại.

Mục tiêu của hệ thống là giúp biên dịch viên giảm thao tác thủ công trong các bước dịch, kiểm tra nhất quán, chỉnh sửa, phê duyệt và dựng lại bản dịch cuối. DRS v3 không chỉ tạo bản dịch thô, mà còn lưu bộ nhớ dự án, kiểm tra thuật ngữ, theo dõi nhân vật, gợi ý quy tắc phong cách và hỗ trợ render chữ dịch trực tiếp lên ảnh manga.

## 2. Vấn đề cần giải quyết

Trong quy trình dịch truyền thống, biên dịch viên thường gặp các vấn đề:

- Dịch nhiều chương/tài liệu dễ lệch thuật ngữ và xưng hô.
- Việc quản lý glossary, tên nhân vật, phong cách văn bản thường rời rạc.
- Kiểm tra bản dịch thủ công tốn thời gian.
- Dịch manga cần thêm OCR, xóa chữ cũ, căn chữ mới, chọn font và render ảnh.
- Các bước dịch, sửa, duyệt, xuất bản thường nằm ở nhiều công cụ khác nhau.

DRS v3 gom các bước này vào một workspace duy nhất, vận hành theo pipeline có trạng thái rõ ràng và có sự can thiệp của người biên tập ở các điểm quan trọng.

## 3. Đối tượng sử dụng

Người dùng chính của DRS v3:

- Biên dịch viên truyện chữ, manga, web novel, fan translation.
- Editor hoặc reviewer cần kiểm tra chất lượng bản dịch.
- Nhóm bản địa hóa cần thống nhất thuật ngữ và phong cách.
- Người quản lý dự án cần theo dõi tiến độ và chất lượng dịch.

## 4. Kiến trúc tổng quan

DRS v3 gồm ba lớp chính:

### Frontend

- Next.js App Router.
- React và TypeScript.
- Tailwind CSS cho giao diện.
- Giao diện chính gồm dashboard dự án, workspace dịch, memory portal và manga bubble editor.

### Backend

- FastAPI.
- SQLite local và khả năng tương thích Cloudflare D1.
- Cloudflare R2 hoặc mock local storage để lưu ảnh, bản render, draft và dữ liệu dự án.
- Các router chính: authentication, projects, documents, translation, memory.

### AI và xử lý dữ liệu

- OCR để nhận diện chữ và vùng chữ trong ảnh.
- Translation Agent để dịch văn bản.
- Consistency Auditor để kiểm tra thuật ngữ, nhân vật và phong cách.
- Project Memory để lưu glossary, entities, style rules và correction log.
- Renderer dùng Pillow để xóa chữ cũ và render chữ dịch lên ảnh manga.

## 5. Các thành phần quan trọng

### Project Dashboard

Dashboard cho phép người dùng tạo, mở, đổi tên và quản lý dự án. Mỗi dự án có thông tin ngôn ngữ nguồn, ngôn ngữ đích, loại nội dung và ghi chú văn phong.

### Translation Workspace

Workspace hoạt động giống một timeline chat. Người dùng có thể nhập yêu cầu dịch, gửi văn bản, upload ảnh manga hoặc chỉnh sửa phản hồi của AI. Trạng thái pipeline được hiển thị trực tiếp để người dùng biết hệ thống đang OCR, truy xuất ngữ cảnh, dịch, review hay render.

### Project Memory

Project Memory là bộ nhớ dài hạn của từng dự án, gồm:

- Glossary: thuật ngữ nguồn và bản dịch chuẩn.
- Entities: nhân vật, tên riêng, đại từ xưng hô, ghi chú.
- Style rules: quy tắc văn phong, cách dùng từ, giọng điệu.
- Correction log: lịch sử chỉnh sửa và phản hồi của người dùng.

Bộ nhớ này giúp AI giữ nhất quán trong các chương hoặc tài liệu dài.

### Manga Bubble Editor

Manga Bubble Editor hỗ trợ workflow dịch ảnh:

1. Upload ảnh manga.
2. OCR và dịch nội dung trong bong bóng thoại.
3. Hiển thị ảnh gốc và các đoạn dịch.
4. Cho phép người dùng sửa từng bubble.
5. Phê duyệt và render bản dịch lên ảnh.
6. Xem ảnh đã render.

Renderer mới tách rõ các bước: đọc OCR box, tìm vùng render, xóa chữ cũ, tính layout, tối ưu font size và vẽ chữ.

## 6. Pipeline dịch văn bản

Luồng dịch văn bản tiêu chuẩn:

1. Người dùng nhập văn bản hoặc yêu cầu dịch.
2. Hệ thống phân tích nội dung và truy xuất Project Memory.
3. Translation Agent tạo bản dịch nháp.
4. Consistency Auditor kiểm tra thuật ngữ, nhân vật và phong cách.
5. Kết quả hiển thị trên timeline cùng điểm QA và cảnh báo.
6. Người dùng sửa trực tiếp hoặc gửi feedback cho AI refine.
7. Người dùng phê duyệt bản dịch.
8. Bản dịch được lưu vào cơ sở dữ liệu và có thể xuất ra tài liệu cuối.

## 7. Pipeline dịch ảnh manga

Luồng dịch ảnh manga:

1. Người dùng upload ảnh.
2. Backend lưu ảnh vào storage và đăng ký asset.
3. OCR hoặc multimodal OCR phát hiện các vùng chữ.
4. Hệ thống dịch nội dung từng bubble sang ngôn ngữ đích.
5. Segment được lưu vào database kèm bbox.
6. Người dùng xem và sửa bản dịch từng bubble.
7. Khi phê duyệt, renderer tạo ảnh đã dịch.
8. Ảnh render được lưu vào storage và hiển thị trong giao diện.

Điểm nổi bật của renderer:

- Không dùng OCR box như vùng render cuối.
- Mở rộng hoặc dò vùng bong bóng thoại để có không gian chữ hợp lý.
- Không xóa cả bubble bằng ellipse trắng cứng.
- Ưu tiên font Unicode hỗ trợ tiếng Việt.
- Tự wrap dòng, căn giữa và tối ưu font size bằng binary search.
- Có chế độ debug hiển thị OCR box, vùng render và layout box.

## 8. Authentication và phân quyền

Hệ thống có đăng ký, đăng nhập bằng username/password và mock Google SSO. Người dùng sau khi đăng nhập nhận JWT token. Backend dùng token để xác thực request và kiểm tra quyền thành viên dự án.

Vai trò cơ bản:

- Viewer: xem nội dung dự án.
- Editor: chỉnh sửa, upload, dịch, render.

## 9. Lưu trữ dữ liệu

DRS v3 dùng nhiều loại dữ liệu:

- Projects: thông tin dự án.
- Documents/chapters: tài liệu hoặc chương.
- Segments: từng đoạn văn hoặc từng bubble manga.
- Assets: ảnh gốc, file upload.
- Rendered assets: ảnh sau khi vẽ dịch.
- Chat history: lịch sử timeline.
- Memory data: glossary, entities, style rules, correction log.

Local mode dùng SQLite và thư mục mock storage. Cloud mode có thể dùng Cloudflare D1 và R2.

## 10. Điểm khác biệt

DRS v3 khác một chatbot dịch thông thường ở các điểm:

- Có workspace theo dự án, không chỉ hỏi đáp đơn lẻ.
- Có bộ nhớ dự án giúp giữ thuật ngữ và nhân vật nhất quán.
- Có pipeline review và QA thay vì chỉ trả bản dịch thô.
- Có editor cho manga và khả năng render chữ lên ảnh.
- Có trạng thái pipeline rõ ràng để người dùng theo dõi tiến độ.
- Có cơ chế phê duyệt để chuyển bản nháp thành bản dịch chính thức.

## 11. Trạng thái hiện tại

Các phần chính đã có:

- Dashboard dự án.
- Workspace dịch dạng chat.
- Upload văn bản và ảnh.
- OCR/dịch ảnh manga.
- Segment editor cho manga.
- Render ảnh manga bằng Pillow.
- Project Memory cho glossary, entities và style rules.
- TypeScript build và Next.js production build chạy được.

Một số điểm có thể cải thiện tiếp:

- Tăng độ chính xác của bubble detection.
- Bổ sung test E2E chạy ổn trong môi trường CI.
- Tối ưu bảo mật cho các URL asset public.
- Hoàn thiện UI/UX cho reviewer và batch export.

## 12. Gợi ý cấu trúc slide

Slide 1: Tên dự án và tagline  
DRS v3 - AI Translation Workspace for Text and Manga Localization.

Slide 2: Bài toán  
Nêu các khó khăn trong dịch dài tập và dịch manga.

Slide 3: Giải pháp  
Một workspace duy nhất cho dịch, review, memory và render.

Slide 4: Kiến trúc hệ thống  
Frontend Next.js, Backend FastAPI, Database, Storage, AI Agents.

Slide 5: Project Memory  
Glossary, Entities, Style Rules, Correction Log.

Slide 6: Text Translation Workflow  
Input -> Memory Retrieval -> Translation -> Audit -> Edit -> Approve.

Slide 7: Manga Translation Workflow  
Upload -> OCR -> Translate -> Edit Bubble -> Render -> Preview.

Slide 8: Manga Renderer  
OCR bbox, render region, text removal, layout engine, font optimization.

Slide 9: Demo User Journey  
Tạo dự án, upload ảnh, sửa bubble, render ảnh dịch.

Slide 10: Giá trị mang lại  
Nhanh hơn, nhất quán hơn, ít thao tác thủ công hơn, phù hợp team dịch.

Slide 11: Trạng thái và hướng phát triển  
Nêu các phần đã hoàn thiện và các hướng nâng cấp.

## 13. Từ khóa cho NotebookLM

- AI translation workspace
- Manga localization
- OCR
- Project memory
- Glossary management
- Entity consistency
- Style rules
- Translation QA
- Bubble rendering
- Human-in-the-loop editing
