import { useState, useEffect } from 'react';
import { Shield, Plus, Phone, Key, Fingerprint, Activity, StopCircle, PlayCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type Tenant = {
    id: number;
    api_id: number;
    api_hash: string;
    phone: string;
    session_name: string;
    is_active: number;
    created_at: string;
};

export function TenantsPage() {
    const [tenants, setTenants] = useState<Tenant[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const [isAdding, setIsAdding] = useState(false);
    const [step, setStep] = useState<1 | 2>(1); // 1: Info, 2: Code

    // Form state
    const [apiId, setApiId] = useState('');
    const [apiHash, setApiHash] = useState('');
    const [phone, setPhone] = useState('');
    const [code, setCode] = useState('');
    const [phoneCodeHash, setPhoneCodeHash] = useState('');
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        fetchTenants();
    }, []);

    const fetchTenants = async () => {
        try {
            const res = await fetch('/api/tenants');
            if (res.ok) {
                const data = await res.json();
                setTenants(data.data);
            }
        } catch (e) {
            console.error('Failed to fetch tenants', e);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSendCode = async () => {
        if (!phone) {
            setError('请输入手机号');
            return;
        }
        setError('');
        setIsSubmitting(true);
        try {
            // Wait for API to send code
            const res = await fetch('/api/tenants/send_code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    phone,
                    api_id: apiId ? parseInt(apiId) : 0,
                    api_hash: apiHash
                })
            });
            const data = await res.json();
            if (res.ok && data.ok) {
                setPhoneCodeHash(data.phone_code_hash);
                setStep(2);
            } else {
                setError(data.detail || '发送验证码失败');
            }
        } catch (e: any) {
            setError(e.message || '请求错误');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleConfirm = async () => {
        if (!code) {
            setError('请输入验证码');
            return;
        }
        setError('');
        setIsSubmitting(true);
        try {
            const res = await fetch('/api/tenants/confirm_login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    phone,
                    code,
                    phone_code_hash: phoneCodeHash
                })
            });
            const data = await res.json();
            if (res.ok && data.ok) {
                setIsAdding(false);
                setStep(1);
                setCode('');
                fetchTenants();
            } else {
                setError(data.detail || '验证失败');
            }
        } catch (e: any) {
            setError(e.message || '请求错误');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleToggleActive = async (id: number, currentActive: number) => {
        try {
            const endpoint = currentActive ? `/api/tenants/${id}` : `/api/tenants/${id}/activate`;
            const method = currentActive ? 'DELETE' : 'POST';
            await fetch(endpoint, { method });
            fetchTenants();
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="flex flex-col h-full max-w-5xl mx-auto">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Shield className="w-6 h-6 text-accent" />
                        多端订阅管理 (Tenant Pool)
                    </h2>
                    <p className="text-text2 mt-1">管理独立运行的 UserBot 工作端，支持多账号并发采集</p>
                </div>
                <button
                    onClick={() => setIsAdding(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-accent/20 text-accent font-medium rounded-lg hover:bg-accent/30 transition-colors border border-accent/20"
                >
                    <Plus className="w-4 h-4" />
                    新增监控终端
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <AnimatePresence>
                    {isAdding && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="glass-panel p-6 rounded-[24px] border border-accent/30 shadow-[0_8px_30px_rgba(255,255,255,0.05)] relative overflow-hidden"
                        >
                            <div className="absolute inset-0 bg-accent/5 pointer-events-none" />
                            <h3 className="text-lg font-medium text-white mb-4 relative z-10">新增监控终端</h3>

                            {error && (
                                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                                    {error}
                                </div>
                            )}

                            {step === 1 ? (
                                <div className="space-y-4 relative z-10">
                                    <div>
                                        <label className="block text-xs text-text2 mb-1.5 uppercase font-medium">手机号 (+86...)</label>
                                        <div className="relative">
                                            <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text2" />
                                            <input
                                                type="text"
                                                value={phone}
                                                onChange={e => setPhone(e.target.value)}
                                                className="w-full bg-black/40 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-white placeholder-white/30 focus:outline-none focus:border-accent"
                                                placeholder="+86..."
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-xs text-text2 mb-1.5 uppercase font-medium">API ID (可选，留空使用默认)</label>
                                        <div className="relative">
                                            <Fingerprint className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text2" />
                                            <input
                                                type="text"
                                                value={apiId}
                                                onChange={e => setApiId(e.target.value)}
                                                className="w-full bg-black/40 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-white placeholder-white/30 focus:outline-none focus:border-accent"
                                                placeholder="7812..."
                                            />
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-xs text-text2 mb-1.5 uppercase font-medium">API HASH (可选)</label>
                                        <div className="relative">
                                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text2" />
                                            <input
                                                type="password"
                                                value={apiHash}
                                                onChange={e => setApiHash(e.target.value)}
                                                className="w-full bg-black/40 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-white placeholder-white/30 focus:outline-none focus:border-accent"
                                                placeholder="abc123def456..."
                                            />
                                        </div>
                                    </div>

                                    <div className="flex gap-3 pt-2">
                                        <button
                                            onClick={() => setIsAdding(false)}
                                            className="flex-1 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors border border-white/10"
                                        >
                                            取消
                                        </button>
                                        <button
                                            onClick={handleSendCode}
                                            disabled={isSubmitting}
                                            className="flex-1 py-2 bg-accent/80 hover:bg-accent text-white font-medium rounded-lg transition-colors border border-transparent shadow-[0_0_15px_rgba(255,255,255,0.2)] disabled:opacity-50"
                                        >
                                            {isSubmitting ? '发送中...' : '发送验证码'}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-4 relative z-10">
                                    <div className="p-3 bg-white/5 rounded-lg border border-white/10 text-sm text-text2 mb-4">
                                        验证码已发送至 Telegram App ({phone})，请查看消息并输入。
                                    </div>
                                    <div>
                                        <label className="block text-xs text-text2 mb-1.5 uppercase font-medium">验证码</label>
                                        <input
                                            type="text"
                                            value={code}
                                            onChange={e => setCode(e.target.value)}
                                            className="w-full bg-black/40 border border-white/10 rounded-lg py-2.5 px-4 text-white text-center tracking-widest text-lg focus:outline-none focus:border-accent"
                                            placeholder="12345"
                                        />
                                    </div>
                                    <div className="flex gap-3 pt-2">
                                        <button
                                            onClick={() => setStep(1)}
                                            className="flex-1 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors border border-white/10"
                                        >
                                            返回重填
                                        </button>
                                        <button
                                            onClick={handleConfirm}
                                            disabled={isSubmitting}
                                            className="flex-1 py-2 bg-accent/80 hover:bg-accent text-white font-medium rounded-lg transition-colors shadow-[0_0_15px_rgba(255,255,255,0.2)] disabled:opacity-50"
                                        >
                                            {isSubmitting ? '验证中...' : '确认并登录'}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>

                {isLoading ? (
                    Array(3).fill(0).map((_, idx) => (
                        <div key={idx} className="h-48 glass-panel rounded-[24px] rounded-lg animate-pulse" />
                    ))
                ) : (
                    tenants.map(tenant => (
                        <motion.div
                            key={tenant.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`glass-panel p-6 rounded-[24px] border ${tenant.is_active ? 'border-white/20 shadow-[0_4px_20px_rgba(255,255,255,0.05)]' : 'border-white/5 opacity-60'} flex flex-col justify-between group transition-all duration-300 hover:border-white/30`}
                        >
                            <div>
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${tenant.is_active ? 'bg-accent/20 text-accent' : 'bg-white/5 text-text3'}`}>
                                            <Shield className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <div className="font-bold text-white text-lg">Tenant #{tenant.id}</div>
                                            <div className="text-xs text-text2">ID: {tenant.api_id || 'System Default'}</div>
                                        </div>
                                    </div>
                                    <div className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${tenant.is_active ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
                                        {tenant.is_active ? 'Active' : 'Stopped'}
                                    </div>
                                </div>

                                <div className="space-y-2.5 mb-6">
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-text2 flex items-center gap-1.5"><Phone className="w-3.5 h-3.5" /> 手机号</span>
                                        <span className="text-white font-mono">{tenant.phone || '未绑定'}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-text2 flex items-center gap-1.5"><Key className="w-3.5 h-3.5" /> Session</span>
                                        <span className="text-white font-mono truncate max-w-[120px]">{tenant.session_name}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-text2 flex items-center gap-1.5"><Activity className="w-3.5 h-3.5" /> 注册时间</span>
                                        <span className="text-text3">{tenant.created_at.split(' ')[0]}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-4 border-t border-white/10 flex gap-2">
                                <button
                                    onClick={() => handleToggleActive(tenant.id, tenant.is_active)}
                                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-colors ${tenant.is_active
                                        ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20'
                                        : 'bg-green-500/10 text-green-500 hover:bg-green-500/20 border border-green-500/20'
                                        }`}
                                >
                                    {tenant.is_active ? <><StopCircle className="w-4 h-4" /> 停用实例</> : <><PlayCircle className="w-4 h-4" /> 启用实例</>}
                                </button>
                                {/* Default seed tenant (id=1) cannot be deleted in UI easily to prevent breaking if not intended, but we just implement stop realistically */}
                            </div>
                        </motion.div>
                    ))
                )}
            </div>
        </div>
    );
}
