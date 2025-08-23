import React, { useEffect, useState } from 'react'
import { Box, Button, Card, CardContent, Typography, Table, TableHead, TableRow, TableCell, TableBody, TableContainer, Paper, Alert, Grid, TextField } from '@mui/material'
import { inspectionApi } from '../services/api'

interface OrderInfoRow {
  id: string
  workOrderId: string
  instructionId: string
  productCode: string
  machineNumber: string
  productionDate: string
  monthlySequence: number
  status?: string
  createdAt?: number
}

export const OrderInfo: React.FC = () => {
  const [rows, setRows] = useState<OrderInfoRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState({ productCode: '', machineNumber: '' })
  const [codeNameOptions, setCodeNameOptions] = useState<Array<{ product_code: string; product_name: string }>>([])

  const load = async () => {
    try {
      setLoading(true)
      const resp = await inspectionApi.searchOrders(50, {
        product_code: filter.productCode || undefined,
        machine_number: filter.machineNumber || undefined,
      })
      setRows(resp.products || [])
    } catch (e) {
      setError('順序情報の読み込みに失敗しました')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // load product code-name master to use as dummy data source
    ;(async () => {
      try {
        const resp = await inspectionApi.listProductTypeNames({ page_size: 500 })
        const items = resp.items || []
        setCodeNameOptions(items.map((x: any) => ({ product_code: x.product_code, product_name: x.product_name })))
      } catch (e) {
        console.warn('Failed to load product code-name master', e)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const createDummy = async () => {
    try {
      setLoading(true)
      if (!codeNameOptions.length) {
        setError('型式コード・型式名マスタに登録がありません。先に登録してください。')
        return
      }
      // pick one from master
      const pick = codeNameOptions[Math.floor(Math.random() * codeNameOptions.length)]
      const now = new Date()
      const y = now.getFullYear(); const m = String(now.getMonth()+1).padStart(2,'0'); const d = String(now.getDate()).padStart(2,'0')
      const productionDate = `${y}-${m}-${d}`
      const suffix = Math.floor(Math.random() * 900 + 100)
      const payload = {
        workOrderId: `WORK-${Date.now().toString().slice(-6)}`,
        instructionId: `INST-${(suffix % 99)+1}`,
        productCode: pick.product_code,
        machineNumber: `MACHINE-${(suffix % 999).toString().padStart(3,'0')}`,
        productionDate,
        monthlySequence: (suffix % 50) + 1,
        qrRawData: undefined,
      }
      await inspectionApi.createOrder(payload)
      await load()
    } catch (e) {
      setError('ダミー順序情報の作成に失敗しました')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>順序情報</Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>
      )}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={3}>
              <TextField size="small" label="型式コード" value={filter.productCode} onChange={(e)=> setFilter(prev => ({...prev, productCode: e.target.value}))} fullWidth />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField size="small" label="機番" value={filter.machineNumber} onChange={(e)=> setFilter(prev => ({...prev, machineNumber: e.target.value}))} fullWidth />
            </Grid>
            <Grid item xs={12} md={6}>
              <Box display="flex" gap={1} justifyContent="flex-end">
                <Button variant="outlined" onClick={load} disabled={loading}>再読込</Button>
                <Button variant="contained" onClick={createDummy} disabled={loading}>ダミー順序情報を作成</Button>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>指図ID</TableCell>
              <TableCell>指示ID</TableCell>
              <TableCell>型式コード</TableCell>
              <TableCell>機番</TableCell>
              <TableCell>生産日</TableCell>
              <TableCell>月連番</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.workOrderId}</TableCell>
                <TableCell>{r.instructionId}</TableCell>
                <TableCell>{r.productCode}</TableCell>
                <TableCell>{r.machineNumber}</TableCell>
                <TableCell>{r.productionDate}</TableCell>
                <TableCell>{r.monthlySequence}</TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}><Typography color="textSecondary">順序情報がありません</Typography></TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default OrderInfo
