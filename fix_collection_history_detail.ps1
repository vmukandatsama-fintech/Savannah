$target = ".\templates\requests_app\collection_history_detail.html"

$content = @'
{% extends "base.html" %}

{% block content %}

<!-- Back -->
<div class="card">
    <a href="{% url 'collection_history' %}" class="back-link">← Back to Collection History</a>
</div>

<!-- Header -->
<div class="card">
    <h2 class="page-title">Collection Detail</h2>

    <div class="info-grid">
        <div class="info-item"><span>Collection Number</span><strong>{{ header.CollectionNumber }}</strong></div>
        <div class="info-item"><span>Collection Date</span><strong>{{ header.CollectionDate|date:"d-m-Y H:i" }}</strong></div>

        <div class="info-item"><span>Request Number</span><strong>{{ header.RequestNumber }}</strong></div>
        <div class="info-item"><span>Status</span><strong>{{ header.StatusName }}</strong></div>

        <div class="info-item"><span>Department</span><strong>{{ header.DepartmentName }}</strong></div>
        <div class="info-item"><span>Disbursed By</span><strong>{{ header.DisbursedByName|default:header.DisbursedBy }}</strong></div>

        <div class="info-item"><span>Farmer</span><strong>{{ header.FarmerName|default:header.Farmer|default:"-" }}</strong></div>
        <div class="info-item"><span>Collector</span><strong>{{ header.CollectorName|default:"-" }}</strong></div>

        <div class="info-item"><span>National ID</span><strong>{{ header.CollectorNationalID|default:"-" }}</strong></div>
        <div class="info-item"><span>Truck</span><strong>{{ header.TruckRegistration|default:"-" }}</strong></div>

        <div class="info-item"><span>Trailer</span><strong>{{ header.TrailerRegistration|default:"-" }}</strong></div>
    </div>
</div>

<!-- Voucher Actions -->
<div class="card">
    <h3 class="section-title">Voucher Actions</h3>

    <div class="voucher-sections">

        <!-- SSRS Voucher -->
        <div class="voucher-panel">
            <h4 class="voucher-subtitle">SSRS Voucher</h4>

            <div class="voucher-grid">
                <div><span>Status</span><strong>{{ header.VoucherStatus|default:"-" }}</strong></div>
                <div><span>Path</span><strong>{{ header.VoucherPath|default:"-" }}</strong></div>
                <div><span>Error</span><strong>{{ header.VoucherError|default:"-" }}</strong></div>
            </div>

            <div class="voucher-actions">
                {% if header.VoucherPath %}
                <a href="{% url 'open_collection_voucher' header.CollectionNumber %}" target="_blank" class="btn btn-primary">
                    Open SSRS Voucher
                </a>

                <a href="{% url 'download_collection_voucher' header.CollectionNumber %}" class="btn btn-light">
                    Download SSRS Voucher
                </a>
                {% endif %}

                <a href="{% url 'regenerate_collection_voucher' header.CollectionNumber %}" onclick="return prepareVoucherWindow();" class="btn btn-secondary">
                    Regenerate SSRS Voucher
                </a>
            </div>
        </div>

        <!-- Django Voucher -->
        <div class="voucher-panel">
            <h4 class="voucher-subtitle">Django Voucher</h4>

            <div class="voucher-grid">
                <div><span>Status</span><strong>{{ header.DjangoVoucherStatus|default:"-" }}</strong></div>
                <div><span>Path</span><strong>{{ header.DjangoVoucherPath|default:"-" }}</strong></div>
                <div><span>Error</span><strong>{{ header.DjangoVoucherError|default:"-" }}</strong></div>
            </div>

            <div class="voucher-actions">
                {% if header.DjangoVoucherPath %}
                <a href="{% url 'open_collection_voucher_django' header.CollectionNumber %}" target="_blank" class="btn btn-primary">
                    Open Django Voucher
                </a>

                <a href="{% url 'download_collection_voucher_django' header.CollectionNumber %}" class="btn btn-light">
                    Download Django Voucher
                </a>
                {% endif %}

                <a href="{% url 'regenerate_collection_voucher_django' header.CollectionNumber %}" class="btn btn-secondary">
                    Regenerate Django Voucher
                </a>
            </div>
        </div>

    </div>
</div>

{% if request.GET.auto_open == "1" %}
<script>
window.addEventListener("load", function () {
    const voucherUrl = "{% url 'open_collection_voucher' header.CollectionNumber %}";
    const hasVoucherPath = "{% if header.VoucherPath %}1{% else %}0{% endif %}";
    const retryCount = parseInt(sessionStorage.getItem("savannah_voucher_retry_count") || "0", 10);
    const maxRetries = 12;

    if (hasVoucherPath === "1") {
        const voucherWindow = window.open(voucherUrl, "savannah_voucher_window");
        try { if (voucherWindow) voucherWindow.focus(); } catch (e) {}
        sessionStorage.clear();
        return;
    }

    if (retryCount < maxRetries) {
        sessionStorage.setItem("savannah_voucher_retry_count", String(retryCount + 1));
        setTimeout(() => window.location.reload(), 1200);
    } else {
        sessionStorage.clear();
    }
});
</script>
{% endif %}

<!-- Items -->
<div class="card">
    <h3 class="section-title">Collection Items</h3>

    <div class="table-wrap">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Line</th>
                    <th>Item Code</th>
                    <th>Item Name</th>
                    <th>UOM</th>
                    <th class="num">Requested</th>
                    <th class="num">This Issue</th>
                    <th class="num">Total Issued</th>
                    <th class="num">Remaining</th>
                    <th>Created</th>
                </tr>
            </thead>
            <tbody>
                {% for line in lines %}
                <tr>
                    <td>{{ line.LineNumber }}</td>
                    <td>{{ line.ItemCode }}</td>
                    <td>{{ line.ItemName }}</td>
                    <td>{{ line.UOM }}</td>

                    <td class="num">{{ line.QuantityRequested|floatformat:0 }}</td>
                    <td class="num">{{ line.ThisIssueQty|floatformat:0 }}</td>

                    <td class="num">
                        {{ line.TotalIssuedToDate|default:"-"|floatformat:0 }}
                    </td>

                    <td class="num">
                        {{ line.RemainingAfterIssue|default:"-"|floatformat:0 }}
                    </td>

                    <td>{{ line.CreatedDate|date:"d-m-Y H:i" }}</td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="9">
                        <div class="empty-state">No collection lines found.</div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<style>
    .page-title {
        margin: 0 0 12px 0;
    }

    .back-link {
        text-decoration: none;
        color: #374151;
        font-weight: 600;
    }

    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 14px;
    }

    .info-item span {
        display: block;
        font-size: 12px;
        color: #6b7280;
    }

    .info-item strong {
        font-size: 14px;
    }

    .voucher-sections {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 16px;
    }

    .voucher-panel {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        background: #fff;
    }

    .voucher-subtitle {
        margin: 0 0 12px 0;
        font-size: 15px;
    }

    .voucher-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
        margin-bottom: 16px;
    }

    .voucher-grid span {
        display: block;
        font-size: 12px;
        color: #6b7280;
    }

    .voucher-grid strong {
        display: block;
        word-break: break-word;
    }

    .voucher-actions {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }

    .table-wrap {
        overflow-x: auto;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
    }

    .data-table {
        width: 100%;
        border-collapse: collapse;
    }

    .data-table th {
        background: #f8fafc;
        padding: 12px;
        font-size: 12px;
        text-transform: uppercase;
    }

    .data-table td {
        padding: 12px;
        border-top: 1px solid #f1f5f9;
    }

    .num {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }

    .empty-state {
        text-align: center;
        padding: 20px;
        color: #6b7280;
    }
</style>

{% endblock %}
'@

if (-not (Test-Path ".\templates\requests_app")) {
    throw "templates\requests_app folder not found. Run this from the Savannah project root."
}

if (Test-Path $target) {
    Copy-Item $target "$target.bak" -Force
    Write-Host "Backup created: $target.bak"
}

Set-Content -Path $target -Value $content -Encoding UTF8

Write-Host "Updated: $target"
Write-Host "Refresh the collection history detail page and test both SSRS and Django voucher buttons."