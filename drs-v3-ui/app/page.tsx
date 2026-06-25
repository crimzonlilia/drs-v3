'use client'

import React from 'react'
import Link from 'next/link'
import { ArrowRight, BookOpen, Layers, Bot, ChevronDown } from 'lucide-react'
import LandingHeader from '@/components/LandingHeader'

export default function Home() {
  return (
    <div className="w-full min-h-screen bg-themeBg text-themeText transition-colors duration-300 relative overflow-hidden flex flex-col">
      {/* Floating Letters Background (Ellipsus style) */}
      <div className="absolute inset-0 pointer-events-none select-none overflow-hidden opacity-20 dark:opacity-10 z-0">
        <span className="absolute text-[12px] font-mono text-slate-500 top-[15%] left-[20%]">a</span>
        <span className="absolute text-[14px] font-mono text-slate-500 top-[10%] left-[45%]">f</span>
        <span className="absolute text-[11px] font-mono text-slate-500 top-[8%] left-[70%]">y</span>
        <span className="absolute text-[16px] font-mono text-slate-500 top-[20%] left-[80%]">w</span>
        <span className="absolute text-[13px] font-mono text-slate-500 top-[35%] left-[10%]">t</span>
        <span className="absolute text-[15px] font-mono text-slate-500 top-[40%] left-[30%]">s</span>
        <span className="absolute text-[12px] font-mono text-slate-500 top-[45%] left-[55%]">b</span>
        <span className="absolute text-[14px] font-mono text-slate-500 top-[38%] left-[85%]">q</span>
        <span className="absolute text-[11px] font-mono text-slate-500 top-[50%] left-[25%]">h</span>
        <span className="absolute text-[15px] font-mono text-slate-500 top-[60%] left-[65%]">p</span>
        <span className="absolute text-[13px] font-mono text-slate-500 top-[55%] left-[90%]">r</span>
        <span className="absolute text-[16px] font-mono text-slate-500 top-[75%] left-[15%]">o</span>
        <span className="absolute text-[12px] font-mono text-slate-500 top-[70%] left-[40%]">k</span>
        <span className="absolute text-[14px] font-mono text-slate-500 top-[80%] left-[50%]">v</span>
        <span className="absolute text-[13px] font-mono text-slate-500 top-[85%] left-[75%]">m</span>
        <span className="absolute text-[15px] font-mono text-slate-500 top-[90%] left-[35%]">g</span>
        <span className="absolute text-[12px] font-mono text-slate-500 top-[92%] left-[88%]">z</span>
      </div>

      <LandingHeader />

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 pt-32 pb-24 text-center relative z-10 max-w-5xl mx-auto w-full">
        {/* Hand-drawn Arrow Sketch (Left) */}
        <div className="absolute left-[5%] top-[40%] md:left-[8%] md:top-[45%] pointer-events-none select-none opacity-40 dark:opacity-30">
          <svg width="120" height="90" viewBox="0 0 120 90" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-slate-500 dark:text-slate-400 stroke-current">
            <path d="M10 80C30 50 60 40 85 45M85 45L70 30M85 45L72 58" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M5 85C4 85 3 84 3 83C3 82 4 81 5 81C7 81 9 82 10 84C10 86 8 87 5 87Z" fill="currentColor"/>
          </svg>
        </div>

        {/* Hand-drawn Cursor/Path Sketch (Right) */}
        <div className="absolute right-[5%] top-[38%] md:right-[10%] md:top-[42%] pointer-events-none select-none opacity-50 dark:opacity-30">
          <svg width="60" height="60" viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-accent-purple dark:text-accent-violet stroke-current fill-current">
            <path d="M15 15L35 22L27 27L22 35L15 15Z" strokeWidth="2" strokeLinejoin="round"/>
            <path d="M26 26L40 40" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-7xl font-serif tracking-tight leading-[1.1] mb-6 max-w-4xl text-themeText">
          Dịch thuật tự nhiên, trọn vẹn văn phong<span className="text-accent-purple">.</span>
        </h1>

        {/* Sub-headline */}
        <p className="text-lg md:text-xl text-themeText/70 max-w-2xl mb-10 leading-relaxed font-sans">
          Oneiros là nền tảng dịch thuật và bản địa hóa thông minh có nhận thức ngữ cảnh, được thiết kế chuyên biệt cho tài liệu chuyên nghiệp, truyện tranh, tiểu thuyết và các tác phẩm sáng tạo.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 mb-16">
          <Link href="/dashboard" className="px-8 py-4 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 rounded-xl text-base font-semibold hover:bg-slate-800 dark:hover:bg-slate-200 shadow-lg hover:shadow-purple-500/10 transition-all flex items-center justify-center gap-2">
            Khám phá Bảng điều khiển
            <ArrowRight size={18} />
          </Link>
          <Link href="/login?mode=register" className="px-8 py-4 glass border border-themeBorder rounded-xl text-base font-semibold hover:bg-slate-100/50 dark:hover:bg-slate-800/50 transition-colors text-themeText">
            Tham gia miễn phí
          </Link>
        </div>

        {/* Scroll Indicator */}
        <div className="animate-bounce mt-4 text-foreground-light/30 dark:text-foreground-dark/30">
          <ChevronDown size={28} />
        </div>
      </main>

      {/* Features Section */}
      <section id="features" className="w-full bg-themeCard/30 py-24 border-t border-themeBorder relative z-10 transition-colors duration-300">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-serif font-bold mb-4">Tính năng nổi bật</h2>
            <p className="text-themeMuted max-w-xl mx-auto text-sm md:text-base">
              Khám phá bộ công cụ dịch thuật nâng cao được thiết kế chuyên biệt cho quy trình bản địa hóa chuyên nghiệp.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="p-8 bg-white/40 dark:bg-slate-900/10 rounded-2xl border border-themeBorder hover:border-accent-purple/30 dark:hover:border-accent-violet/30 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-accent-purple/10 dark:bg-accent-purple/20 flex items-center justify-center text-accent-purple dark:text-accent-violet mb-6 group-hover:scale-110 transition-transform">
                <BookOpen size={24} />
              </div>
              <h3 className="text-lg font-bold mb-3">Nhận thức Ngữ cảnh</h3>
              <p className="text-sm text-themeMuted leading-relaxed">
                Tự động tối ưu hóa ngữ cảnh bản dịch bằng cách nạp bộ nhớ Fandom, thuật ngữ glossary, quy tắc danh xưng nhân vật và cấu hình dự án một cách linh hoạt.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-8 bg-white/40 dark:bg-slate-900/10 rounded-2xl border border-themeBorder hover:border-accent-cyan/30 dark:hover:border-accent-cyan/30 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-accent-cyan/10 dark:bg-accent-cyan/20 flex items-center justify-center text-accent-cyan mb-6 group-hover:scale-110 transition-transform">
                <Bot size={24} />
              </div>
              <h3 className="text-lg font-bold mb-3">Kiểm duyệt Kép bằng AI</h3>
              <p className="text-sm text-themeMuted leading-relaxed">
                Tự động sinh các phương án dịch nháp, chạy quét lỗi bằng hệ thống đánh giá tính nhất quán và hoàn thiện câu từ qua AI kiểm duyệt chuyên biệt.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-8 bg-white/40 dark:bg-slate-900/10 rounded-2xl border border-themeBorder hover:border-accent-purple/30 dark:hover:border-accent-violet/30 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-accent-purple/10 dark:bg-accent-purple/20 flex items-center justify-center text-accent-purple dark:text-accent-violet mb-6 group-hover:scale-110 transition-transform">
                <Layers size={24} />
              </div>
              <h3 className="text-lg font-bold mb-3">Chốt duyệt & Đóng góp từ</h3>
              <p className="text-sm text-themeMuted leading-relaxed">
                Phê duyệt nhanh các câu dịch, đồng thời dễ dàng thêm các thuật ngữ mới vào glossary của dự án trực tiếp từ không gian làm việc của biên tập viên.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Workflow Section */}
      <section id="pipeline" className="w-full py-24 border-t border-themeBorder relative z-10">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-serif font-bold mb-4">Quy trình Dịch thuật Chuẩn xác</h2>
            <p className="text-themeMuted max-w-lg mx-auto text-sm md:text-base">
              Quy trình ba giai đoạn toàn diện đảm bảo sự nhất quán tuyệt đối về thuật ngữ và sự thanh thoát trong văn phong.
            </p>
          </div>

          <div className="space-y-12">
            {/* Step 1 */}
            <div className="flex gap-6 items-start">
              <div className="w-8 h-8 rounded-full bg-accent-purple text-white flex items-center justify-center font-bold text-sm shrink-0">
                1
              </div>
              <div>
                <h3 className="text-lg font-bold mb-2">Bước 1 — Phân tích ngữ cảnh & Sinh bản dịch</h3>
                <p className="text-sm text-themeMuted leading-relaxed">
                  Tích hợp các ràng buộc từ bộ nhớ dự án, đánh giá các biến ngữ cảnh và tạo ra các bản dịch nháp ứng viên chất lượng cao.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex gap-6 items-start">
              <div className="w-8 h-8 rounded-full bg-accent-cyan text-white flex items-center justify-center font-bold text-sm shrink-0">
                2
              </div>
              <div>
                <h3 className="text-lg font-bold mb-2">Bước 2 — Tự động Kiểm tra Nhất quán</h3>
                <p className="text-sm text-themeMuted leading-relaxed">
                  Tự động quét và đối chiếu các quy chuẩn văn phong, cách xưng hô của nhân vật và thuật ngữ glossary để phát hiện sai lệch ngay lập tức.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex gap-6 items-start">
              <div className="w-8 h-8 rounded-full bg-accent-purple text-white flex items-center justify-center font-bold text-sm shrink-0">
                3
              </div>
              <div>
                <h3 className="text-lg font-bold mb-2">Bước 3 — Biên tập & Duyệt bản dịch</h3>
                <p className="text-sm text-themeMuted leading-relaxed">
                  Chỉnh sửa các phương án dịch song song trực quan với văn bản gốc, kiểm tra bố cục trang và trực tiếp đồng bộ các từ khóa mới vào từ điển hệ thống.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer id="about" className="w-full py-12 border-t border-themeBorder text-center relative z-10">
        <p className="text-xs text-themeMuted/50">
          &copy; {new Date().getFullYear()} Oneiros. Phát triển trên nền Next.js & Trí tuệ nhân tạo.
        </p>
      </footer>
    </div>
  )
}
