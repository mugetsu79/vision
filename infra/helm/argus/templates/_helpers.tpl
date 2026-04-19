{{- define "argus.name" -}}
argus
{{- end -}}

{{- define "argus.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "argus.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "argus.labels" -}}
app.kubernetes.io/name: {{ include "argus.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "argus.image" -}}
{{- printf "%s/%s:%s" .registry .repository .tag -}}
{{- end -}}
